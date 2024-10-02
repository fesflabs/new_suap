# -*- coding: utf-8 -*-


import datetime

from django.conf import settings

from arquivo.tests.test_views import UnidadeOrganizacional
from comum.models import Vinculo
from comum.utils import get_sigla_reitoria
from djtools import forms
from djtools.forms import AutocompleteWidget
from djtools.forms.widgets import CheckboxTooltipSelectPlus, FilteredSelectMultiplePlus
from djtools.utils import send_notification
from edu.models import Aluno
from edu.models.cursos import CursoCampus
from edu.models.diretorias import Diretoria
from edu.models.turmas import Turma
from etep.models import (
    Categoria,
    AcompanhamentoCategoria,
    RegistroAcompanhamento,
    Acompanhamento,
    AcompanhamentoEncaminhamento,
    SolicitacaoAcompanhamentoCategoria,
    Interessado,
    Encaminhamento,
    SolicitacaoAcompanhamento,
    RegistroAcompanhamentoInteressado,
    Documento,
)


class AcompanhamentoForm(forms.ModelFormPlus):
    aluno = forms.ModelChoiceFieldPlus(Aluno.locals_uo, required=True)
    categorias = forms.MultipleModelChoiceFieldPlus(Categoria.objects, label='Tipos', widget=CheckboxTooltipSelectPlus(tooltip_field='descricao'))
    descricao = forms.CharField(label='Descrição', required=True, widget=forms.Textarea())

    class Meta:
        model = Acompanhamento
        exclude = ()

    def __init__(self, *args, **kwargs):
        super(AcompanhamentoForm, self).__init__(*args, **kwargs)
        categorias = Categoria.objects.filter(id__in=self.instance.acompanhamentocategoria_set.values_list('categoria', flat=True))
        self.fields['categorias'].initial = categorias

    def save(self, *args, **kwargs):
        categorias = self.cleaned_data.get('categorias')
        descricao = self.cleaned_data.get('descricao')
        obj = super(AcompanhamentoForm, self).save(*args, **kwargs)
        self.instance.save()
        AcompanhamentoCategoria.objects.filter(acompanhamento=obj).delete()
        for categoria in categorias:
            AcompanhamentoCategoria.objects.get_or_create(categoria=categoria, acompanhamento=obj)
        if not RegistroAcompanhamento.objects.filter(acompanhamento=obj).exists():
            RegistroAcompanhamento.objects.create(acompanhamento=obj, descricao=descricao, situacao=RegistroAcompanhamento.EM_ACOMPANHAMENTO)
        return obj


class RegistroAcompanhamentoForm(forms.ModelFormPlus):
    interessados = forms.MultipleModelChoiceFieldPlus(
        Interessado.objects,
        label='Tornar visível para interessados',
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text='A ETEP sempre terá acesso a todos os registros',
    )

    class Meta:
        model = RegistroAcompanhamento
        exclude = ('acompanhamento', 'situacao')

    def __init__(self, acompanhamento, *args, **kwargs):
        super(RegistroAcompanhamentoForm, self).__init__(*args, **kwargs)
        self.instance.acompanhamento = acompanhamento
        self.fields['descricao'].required = True
        self.fields['interessados'].queryset = Interessado.objects.filter(acompanhamento=acompanhamento, ativado=True).exclude(vinculo__user=self.request.user)
        self.fields['interessados'].initial = RegistroAcompanhamentoInteressado.objects.filter(registro_acompanhamento=self.instance).values_list('interessado', flat=True)

    def processar(self):
        interessados = self.cleaned_data.get('interessados')
        RegistroAcompanhamentoInteressado.objects.filter(registro_acompanhamento=self.instance).delete()
        vinculos = []
        for membro in self.instance.acompanhamento.get_membros_etep():
            vinculos.append(membro.get_vinculo())

        # se for o proprio interessado cadastrando um registro
        funcionario = Interessado.objects.filter(acompanhamento=self.instance.acompanhamento, vinculo__user=self.request.user)
        if funcionario.exists():
            RegistroAcompanhamentoInteressado.objects.get_or_create(interessado=funcionario[0], registro_acompanhamento=self.instance, data_ciencia=datetime.datetime.now())

        # cadastrando todos os interessados
        for interessado in interessados:
            RegistroAcompanhamentoInteressado.objects.get_or_create(interessado=interessado, registro_acompanhamento=self.instance)
            vinculos.append(interessado.vinculo)
        if vinculos:
            self.instance.enviar_emails(vinculos)


class SituacaoAcompanhamentoForm(forms.ModelFormPlus):
    class Meta:
        model = RegistroAcompanhamento
        fields = ('situacao',)

    def __init__(self, acompanhamento, *args, **kwargs):
        super(SituacaoAcompanhamentoForm, self).__init__(*args, **kwargs)
        self.instance.acompanhamento = acompanhamento

    def clean(self):
        if self.instance.acompanhamento.situacao == self.cleaned_data.get('situacao'):
            raise forms.ValidationError('Esta já é a situação atual.')
        if (
            self.cleaned_data.get('situacao') == RegistroAcompanhamento.ACOMPANHAMENTO_FINALIZADO
            and not AcompanhamentoEncaminhamento.objects.filter(acompanhamento=self.instance.acompanhamento).exists()
        ):
            raise forms.ValidationError('É necessário registrar pelo menos um encaminhamento para finalizar o acompanhamento.')


class SolicitacaoAcompanhamentoForm(forms.ModelFormPlus):
    categorias = forms.ModelMultipleChoiceField(Categoria.objects, label='Tipos', widget=FilteredSelectMultiplePlus('', True))
    aluno = forms.ModelChoiceFieldPlus(Aluno.objects, required=True)

    class Meta:
        model = SolicitacaoAcompanhamento
        fields = ('aluno', 'descricao')

    def __init__(self, *args, **kwargs):
        super(SolicitacaoAcompanhamentoForm, self).__init__(*args, **kwargs)
        categorias = Categoria.objects.filter(id__in=self.instance.solicitacaoacompanhamentocategoria_set.values_list('categoria', flat=True))
        self.fields['categorias'].initial = categorias
        if self.request.GET.get('diario'):
            diario_pk = self.request.GET.get('diario')
            self.fields['aluno'].queryset = Aluno.objects.filter(matriculaperiodo__matriculadiario__diario__pk=diario_pk).distinct()

        elif self.request.user.get_profile().funcionario.setor.uo.sigla != get_sigla_reitoria():
            self.fields['aluno'].queryset = Aluno.objects.filter(curso_campus__diretoria__setor__uo=self.request.user.get_profile().funcionario.setor.uo).distinct()

    def save(self, *args, **kwargs):
        categorias = self.cleaned_data.get('categorias')
        obj = super(SolicitacaoAcompanhamentoForm, self).save(*args, **kwargs)
        self.instance.save()
        for categoria in categorias:
            SolicitacaoAcompanhamentoCategoria.objects.get_or_create(categoria=categoria, solicitacao=obj)
        return obj


class InteressadosForm(forms.FormPlus):
    vinculos = forms.MultipleModelChoiceFieldPlus(Vinculo.objects.funcionarios_ativos(), label='Interessados', required=False)

    def __init__(self, acompanhamento, *args, **kwargs):
        self.acompanhamento = acompanhamento
        super(InteressadosForm, self).__init__(*args, **kwargs)

    def processar(self):
        url_acompanhamento = settings.SITE_URL + self.acompanhamento.get_absolute_url()
        for vinculo in self.cleaned_data.get('vinculos'):
            interessado, criado = Interessado.objects.get_or_create(acompanhamento=self.acompanhamento, vinculo=vinculo)
            if criado:
                titulo = '[SUAP] Interessado ETEP'
                texto = """<h1>Interessado ETEP</h1>
                    <p>Você foi adicionado(a) pelo(a) servidor(a) %s ao acompanhamento do(a) aluno(a) %s.
                    <a href="%s">Clique aqui</a> para verificar o acompanhamento,
                    ou acesse todos os acompanhamentos através no menu Ensino -> ETEP - > Acompanhamentos.</p>
                    """ % (
                    self.request.user,
                    self.acompanhamento.aluno,
                    url_acompanhamento,
                )
                send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [vinculo])


class NotificarInteressadosForm(forms.FormPlus):
    interessados = forms.MultipleModelChoiceFieldPlus(Interessado.objects, label='Interessados', required=False, widget=forms.CheckboxSelectMultiple)

    def __init__(self, registro, *args, **kwargs):
        self.registro = registro
        self.eh_acompanhamento = hasattr(self.registro, 'descricao')
        super(NotificarInteressadosForm, self).__init__(*args, **kwargs)
        self.fields['interessados'].queryset = Interessado.objects.filter(acompanhamento=self.registro.acompanhamento).exclude(vinculo__user=self.request.user)
        self.fields['interessados'].initial = RegistroAcompanhamentoInteressado.objects.filter(registro_acompanhamento=self.registro).values_list('interessado', flat=True)

    def processar(self):
        interessados = self.cleaned_data.get('interessados')
        RegistroAcompanhamentoInteressado.objects.filter(registro_acompanhamento=self.registro).exclude(interessado__in=interessados).exclude(
            interessado__vinculo__user=self.request.user
        ).delete()
        vinculos = []
        for interessado in interessados:
            RegistroAcompanhamentoInteressado.objects.get_or_create(interessado=interessado, registro_acompanhamento=self.registro)
            vinculos.append(interessado.vinculo)
        if vinculos:
            self.registro.enviar_emails(vinculos)


class AdicionarEncaminhamentosForm(forms.FormPlus):
    encaminhamentos = forms.ModelMultipleChoiceField(Encaminhamento.objects, label='Encaminhamentos', required=False, widget=FilteredSelectMultiplePlus('', True))

    def __init__(self, acompanhamento, *args, **kwargs):
        self.acompanhamento = acompanhamento
        super(AdicionarEncaminhamentosForm, self).__init__(*args, **kwargs)
        self.fields['encaminhamentos'].queryset = Encaminhamento.objects.exclude(
            id__in=self.acompanhamento.acompanhamentoencaminhamento_set.values_list('encaminhamento__id', flat=True)
        )

    def processar(self):
        for encaminhamento in self.cleaned_data.get('encaminhamentos'):
            AcompanhamentoEncaminhamento.objects.get_or_create(acompanhamento=self.acompanhamento, encaminhamento=encaminhamento)


class DocumentoForm(forms.ModelFormPlus):
    def __init__(self, atividade, *args, **kwargs):
        super(DocumentoForm, self).__init__(*args, **kwargs)
        self.instance.atividade = atividade

    class Meta:
        model = Documento
        exclude = ('atividade',)


class RelatorioAcompanhamentoForm(forms.Form):
    SUBMIT_LABEL = 'Consultar'
    METHOD = 'get'
    categorias = forms.ModelMultiplePopupChoiceField(Categoria.objects, label='Categorias', required=False)
    campi = forms.ModelMultiplePopupChoiceField(UnidadeOrganizacional.locals, label='Campi', required=False)
    diretorias = forms.ModelMultiplePopupChoiceField(
        Diretoria.objects.none(), label='Diretorias', required=False, widget=AutocompleteWidget(multiple=True, search_fields=Diretoria.SEARCH_FIELDS, form_filters=[('campi', 'setor__uo__in')])
    )
    cursos = forms.MultipleModelChoiceFieldPlus(
        CursoCampus.locals,
        label='Cursos',
        required=False,
        widget=AutocompleteWidget(multiple=True, search_fields=CursoCampus.SEARCH_FIELDS, form_filters=[('campi', 'diretoria__setor__uo__in'), ('diretorias', 'diretoria__in')]),
    )
    turmas = forms.MultipleModelChoiceFieldPlus(
        Turma.objects.none(),
        label='Turmas',
        required=False,
        widget=AutocompleteWidget(
            multiple=True,
            search_fields=Turma.SEARCH_FIELDS,
            form_filters=[('campi', 'curso_campus__diretoria__setor__uo__in'), ('diretorias', 'curso_campus__diretoria__in'), ('cursos', 'curso_campus__in')],
        ),
    )
    aluno = forms.ModelChoiceFieldPlus(Aluno.locals_diretoria, label='Aluno', required=False)
    vinculo = forms.ModelChoiceFieldPlus(Vinculo.objects, label='Interessado', required=False)

    def __init__(self, *args, **kwargs):
        super(RelatorioAcompanhamentoForm, self).__init__(*args, **kwargs)
        self.fields['diretorias'].queryset = Diretoria.locals
        self.fields['turmas'].queryset = Turma.locals
        self.fields['vinculo'].queryset = Vinculo.objects.funcionarios()

    def processar(self):
        qs = Acompanhamento.locals.all()

        categorias = self.cleaned_data['categorias']
        campi = self.cleaned_data['campi']
        diretorias = self.cleaned_data['diretorias']
        cursos = self.cleaned_data['cursos']
        turmas = self.cleaned_data['turmas']
        aluno = self.cleaned_data['aluno']
        vinculo = self.cleaned_data['vinculo']

        if categorias:
            qs = qs.filter(acompanhamentocategoria__categoria__in=categorias)
        if campi:
            qs = qs.filter(aluno__curso_campus__diretoria__setor__uo__in=campi)
        if diretorias:
            qs = qs.filter(aluno__curso_campus__diretoria__in=diretorias)
        if cursos:
            qs = qs.filter(aluno__curso_campus__in=cursos)
        if turmas:
            qs = qs.filter(aluno__matriculaperiodo__turma__in=turmas)
        if aluno:
            qs = qs.filter(aluno=aluno)
        if vinculo:
            qs = qs.filter(interessado__vinculo=vinculo)

        return qs
