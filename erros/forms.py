import datetime
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.forms import TextInput, Textarea

from comum.models import Vinculo
from djtools import forms
from djtools.forms import AutocompleteWidget
from djtools.templatetags.filters import in_group
from djtools.utils import get_client_ip
from erros.utils import get_custom_view_name_from_url, get_sentry_issue_id_from_url
from erros.models import (
    InteressadoErro,
    Erro, HistoricoComentarioErro
)
from erros.utils import get_apps_disponiveis, get_hostname


class ErroForm(forms.ModelFormPlus):
    url = forms.CharFieldPlus(label='URL do SUAP')
    url_sentry = forms.CharFieldPlus(label='URL da Issue do Sentry', required=False)
    gitlab_issue_url = forms.CharFieldPlus(label='URL da Issue do Gitlab', required=False)

    class Meta:
        model = Erro
        exclude = ('view', 'qtd_vinculos_afetados')

    def clean_url(self):
        if not get_custom_view_name_from_url(self.cleaned_data.get('url')):
            raise ValidationError('URL inválida.')
        self.instance.view = get_custom_view_name_from_url(self.cleaned_data.get('url'))
        return self.cleaned_data['url']

    def clean_url_sentry(self):
        if not self.cleaned_data['url_sentry']:
            return None
        return self.cleaned_data['url_sentry']


class ReportarErroForm(forms.FormPlus):
    url = forms.CharField(label='URL com Erro', widget=TextInput(attrs={'readonly': 'readonly'}), required=True, help_text='É importante reportar o erro diretamente da página em que o erro esteja acontecendo, ou, diante da impossibilidade, da página imediatamente anterior')
    descricao = forms.CharField(label='Descreva a operação que você estava realizando antes de ocorrer o erro e a mensagem de erro que o sistema apresentou', help_text='Esta descrição necessariamente não deverá conter dados privados, pois será um erro visível a todos os usuários', widget=Textarea(), required=True)

    def __init__(self, *args, **kwargs):
        url = kwargs.pop('url')
        super().__init__(*args, **kwargs)
        self.fields['url'].initial = url

    def clean_url(self):
        if not get_custom_view_name_from_url(self.cleaned_data.get('url', '')):
            raise ValidationError('URL inválida.')
        return self.cleaned_data['url']

    def processar(self):
        erro = Erro()
        erro.descricao = self.cleaned_data.get('descricao')
        erro.url = self.cleaned_data.get('url')
        erro.view = get_custom_view_name_from_url(erro.url)
        erro.informante = self.request.user.get_vinculo()
        erro.agent = self.request.META.get('HTTP_USER_AGENT', '-')
        erro.ip_address = get_client_ip(self.request)
        erro.maquina = get_hostname()
        erro.criar()
        return erro


class ReportarErroPorChamadoForm(forms.FormPlus):
    url = forms.CharField(label='URL com Erro', required=True, help_text='Informe a URL completa da página onde o erro ocorre.')
    descricao = forms.CharField(label='Descreva a operação que você estava realizando antes de ocorrer o erro', help_text='Esta descrição necessariamente não deverá conter dados privados, pois será um erro visível a todos os usuários', widget=Textarea(), required=True)

    def clean_url(self):
        if not get_custom_view_name_from_url(self.cleaned_data.get('url', '')):
            raise ValidationError('URL inválida.')
        return self.cleaned_data['url']

    def processar(self, chamado):
        interessados_chamado = chamado.get_vinculos_interessados()
        erro = Erro()
        erro.descricao = self.cleaned_data.get('descricao')
        erro.url = self.cleaned_data.get('url')
        erro.view = get_custom_view_name_from_url(erro.url)
        erro.informante = self.request.user.get_vinculo()
        erro.agent = self.request.META.get('HTTP_USER_AGENT', '-')
        erro.ip_address = get_client_ip(self.request)
        erro.criar()

        descricao = f'Erro reportado automaticamente a partir do chamado <a href="{chamado.get_absolute_url()}">#{chamado.pk}</a>'
        HistoricoComentarioErro.objects.create(erro=erro, descricao=descricao, tipo=HistoricoComentarioErro.TIPO_COMENTARIO, automatico=True)

        for interessado in interessados_chamado:
            erro.gerenciar_interessado(interessado, habilitar=True, mensagem_customizada=f'foi adicionado automaticamente como interessado a partir do chamado: <a href="{chamado.get_absolute_url()}">#{chamado.pk}</a>.')

        comunicacao = chamado.criar_comunicacao(self.request.user, datetime.datetime.now(), f'Foi reportado o erro <a href="{erro.get_absolute_url()}">#{erro.pk}</a> relacionado a este chamado.')
        comunicacao.mensagem_automatica = True
        comunicacao.save()


class ComentarioErroForm(forms.FormPlus):
    descricao = forms.CharField(label='Descrição da atividade', widget=Textarea())

    def processar(self, erro, vinculo, tipo):
        erro.comentar(vinculo=vinculo, descricao=self.cleaned_data.get('descricao'), tipo=tipo)


class SituacaoErroForm(forms.FormPlus):
    descricao = forms.CharField(label='Motivo', widget=Textarea(), required=True)

    def processar(self, erro, vinculo, situacao_id):
        erro.gerenciar_situacao(vinculo=vinculo, situacao=situacao_id, motivo=self.cleaned_data.get('descricao'))


class InteressadoErroForm(forms.FormPlus):
    interessado = forms.ModelChoiceFieldPlus(label='Interessado', queryset=Vinculo.objects, required=True)

    def __init__(self, *args, **kwargs):
        self.erro = kwargs.pop('erro')
        super().__init__(*args, **kwargs)
        self.fields['interessado'].queryset = Vinculo.objects.exclude(interessadoerro__erro=self.erro)

    def save(self):
        interessado = self.cleaned_data.get('interessado')
        InteressadoErro.objects.get_or_create(vinculo=interessado, erro=self.erro)
        self.erro.gerenciar_interessado(self.request.user.get_vinculo(), self.cleaned_data.get('interessado'))


class ModulosForm(forms.FormPlus):
    METHOD = 'POST'
    modulo = forms.ChoiceField(choices=[(c.label, c.verbose_name) for c in get_apps_disponiveis()])


class BuscarErrosForm(forms.FormPlus):
    METHOD = 'GET'
    TODOS = 'todos'
    SIM = 'sim'
    NAO = 'nao'
    SIM_NAO_CHOICES = [[SIM, "Sim"], [NAO, "Não"]]
    busca = forms.CharFieldPlus(label='Busca Textual', required=False, widget=TextInput(attrs={'placeholder': 'Informar URL'}))
    sou_interessado = forms.ChoiceField(choices=SIM_NAO_CHOICES, label='Sou Interessado', required=False, widget=AutocompleteWidget())
    atendente_atual = forms.ModelChoiceFieldPlus(Vinculo.objects, label='Atendente Atual', required=False)
    modulo = forms.ChoiceField(choices=[[c.label, c.verbose_name] for c in get_apps_disponiveis()], label='Módulos', required=False, widget=AutocompleteWidget())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.eh_desenvolvedor = in_group(self.request.user, 'Desenvolvedor', ignore_if_superuser=False)
        self.eh_recebedor = in_group(self.request.user, 'Recebedor de Demandas', ignore_if_superuser=False)
        self.fields['atendente_atual'].queryset = Vinculo.objects.filter(user__usuariogrupo__group__name='Desenvolvedor')

        if self.eh_desenvolvedor:
            self.fields['busca'].widget.attrs = {'placeholder': 'Informar URL ou View'}
            self.fields['possui_url_gitlab'] = forms.ChoiceField(choices=self.SIM_NAO_CHOICES, label='Possui URL no Gitlab?', required=False, widget=AutocompleteWidget())
            self.fields['possui_url_sentry'] = forms.ChoiceField(choices=self.SIM_NAO_CHOICES, label='Possui URL no Sentry', required=False, widget=AutocompleteWidget())

        if self.eh_recebedor:
            self.fields['sem_atribuicao'] = forms.ChoiceField(choices=self.SIM_NAO_CHOICES, label='Sem atribuição', required=False, widget=AutocompleteWidget())

    def processar(self):
        busca = self.cleaned_data.get('busca')
        possui_url_gitlab = self.cleaned_data.get('possui_url_gitlab')
        possui_url_sentry = self.cleaned_data.get('possui_url_sentry')
        sou_interessado = self.cleaned_data.get('sou_interessado')
        modulo = self.cleaned_data.get('modulo')
        atendente_atual = self.cleaned_data.get('atendente_atual')
        sem_atribuicao = self.cleaned_data.get('sem_atribuicao')

        qs = Erro.objects.all()

        if busca:
            qs = qs.filter(url__icontains=busca) | qs.filter(view__icontains=busca)

        if possui_url_gitlab == self.SIM:
            qs = qs.filter(gitlab_issue_url__icontains='http')
        elif possui_url_gitlab == self.NAO:
            qs = qs.exclude(gitlab_issue_url__icontains='http')

        if possui_url_sentry == self.SIM:
            qs = qs.filter(url_sentry__icontains='http')
        elif possui_url_sentry == self.NAO:
            qs = qs.exclude(url_sentry__icontains='http')

        if sou_interessado == self.SIM:
            qs = qs.filter(interessadoerro__vinculo=self.request.user.get_vinculo())
        elif sou_interessado == self.NAO:
            qs = qs.exclude(interessadoerro__vinculo=self.request.user.get_vinculo())

        if sem_atribuicao == self.SIM:
            qs = qs.filter(atendente_atual__isnull=True)
        elif sem_atribuicao == self.NAO:
            qs = qs.exclude(atendente_atual__isnull=True)

        if modulo:
            qs = qs.filter(view__icontains=modulo)

        if atendente_atual:
            qs = qs.filter(atendente_atual=atendente_atual)

        if not self.eh_desenvolvedor:
            qs = qs.exclude(situacao=Erro.SITUACAO_CANCELADO) | qs.filter(situacao=Erro.SITUACAO_CANCELADO, interessadoerro__vinculo=self.request.user.get_vinculo())

        return qs.distinct()


class AlterarURLErroForm(forms.FormPlus):
    url = forms.CharFieldPlus(label='Nova URL com Erro')

    def __init__(self, *args, **kwargs):
        self.erro = kwargs.pop('erro')
        self.vinculo = kwargs.pop('vinculo')
        self.tipo = kwargs.pop('tipo')
        self.issue_id = None
        super().__init__(*args, **kwargs)
        required = False
        if self.tipo == 'erro':
            label = 'Nova URL do Erro'
            required = True
        elif self.tipo == 'sentry':
            label = 'Nova URL do Erro do Sentry'
        elif self.tipo == 'gitlab':
            label = 'Nova URL da Issue no Gitlab'
        else:
            label = 'Nova URL'
        self.fields['url'].label = label
        self.fields['url'].required = required

    def clean_url(self):
        url = self.cleaned_data.get('url')
        if self.tipo == 'erro':
            view = get_custom_view_name_from_url(url)
            if not view:
                raise ValidationError('URL inválida.')
        elif self.tipo == 'sentry':
            if url:
                URLValidator()(url)
                self.issue_id = get_sentry_issue_id_from_url(url)
                if not self.issue_id:
                    raise ValidationError('URL do Sentry inválida.')
                else:
                    self.issue_id = str(self.issue_id)
            else:
                self.issue_id = None
        else:
            if url:
                URLValidator()(url)
        return url

    def processar(self):
        url = self.cleaned_data.get('url')
        self.erro.alterar_url(self.vinculo, url, self.tipo, self.issue_id)


class AnexoErroForm(forms.FormPlus):
    descricao = forms.CharFieldPlus(label='Descrição', max_length=80)
    arquivo = forms.FileFieldPlus(filetypes=['xls', 'csv', 'doc', 'pdf', 'jpg', 'png'])

    def __init__(self, *args, **kwargs):
        self.erro = kwargs.pop('erro')
        self.anexado_por = kwargs.pop('vinculo')
        super().__init__(*args, **kwargs)

    def processar(self):
        descricao = self.cleaned_data.get('descricao')
        arquivo = self.cleaned_data.get('arquivo')
        self.erro.anexar(self.anexado_por, descricao, arquivo)


class AtribuirErroForm(forms.FormPlus):
    atendente = forms.ModelChoiceFieldPlus(Vinculo.objects, required=True)

    def __init__(self, *args, **kwargs):
        self.erro = kwargs.pop('erro')
        self.atribuinte = kwargs.pop('atribuinte')
        super().__init__(*args, **kwargs)
        self.fields['atendente'].queryset = Vinculo.objects.filter(user__usuariogrupo__group__name__in=['Analista', 'Desenvolvedor']).distinct()

    def processar(self):
        atribuido = self.cleaned_data.get('atendente')
        self.erro.atribuir(self.atribuinte, atribuido)


class UnificarErroForm(forms.FormPlus):
    erros = forms.MultipleModelChoiceFieldPlus(Erro.objects, help_text='Serão listados apenas os erros que possuem a view idêntica a do erro principal. Pode-se usar o id e a url para realizar a busca.')

    def __init__(self, *args, **kwargs):
        self.erro = kwargs.pop('erro')
        self.vinculo = kwargs.pop('vinculo')
        super().__init__(*args, **kwargs)
        self.fields['erros'].queryset = Erro.objects.filter(view=self.erro.view).exclude(situacao__in=Erro.SITUACOES_FINAIS).exclude(id=self.erro.id)

    def processar(self):
        erros = self.cleaned_data.get('erros')
        self.erro.unificar(self.vinculo, erros)


class EditarAtualizacaoErroForm(forms.ModelFormPlus):
    class Meta:
        model = Erro
        fields = ('titulo_atualizacao', 'tipo_atualizacao', 'grupos_atualizacao')

    def __init__(self, *args, **kwargs):
        self.required = kwargs.pop('required', True)
        super().__init__(*args, **kwargs)
        self.fields['tipo_atualizacao'].choices = (('', ''),) + Erro.TIPO_CHOICES
        if not self.required:
            self.fields['titulo_atualizacao'].required = False
            self.fields['tipo_atualizacao'].required = False
            self.fields['grupos_atualizacao'].required = False
            self.EXTRA_BUTTONS = [dict(name='pular', value='Pular')]

    def clean(self):
        titulo_atualizacao = self.cleaned_data.get('titulo_atualizacao')
        tipo_atualizacao = self.cleaned_data.get('tipo_atualizacao')
        grupos_atualizacao = self.cleaned_data.get('grupos_atualizacao')
        if self.request.POST.get('pular'):
            return self.cleaned_data
        if not self.required and not ((titulo_atualizacao and tipo_atualizacao and grupos_atualizacao) or (not titulo_atualizacao and not tipo_atualizacao and not grupos_atualizacao)):
            raise ValidationError('Para criar uma atualização, você deve preencher todos os campos. Deixe todos os campos vazios, se não quiser criar uma atualização.')
