# -*- coding: utf-8 -*-
import datetime
import random
import string

from djtools.forms.fields.captcha import ReCaptchaField

from avaliacao_integrada.models import Indicador, TipoAvaliacao, Segmento, Avaliacao, Macroprocesso, Eixo, Resposta, Dimensao
from comum.models import Ano
from djtools import forms
from djtools.forms import FilteredSelectMultiplePlus
from edu.models import Modalidade, CursoCampus
from rh.models import AreaVinculacao, UnidadeOrganizacional


class EixoForm(forms.ModelFormPlus):
    ordem = forms.ChoiceField(choices=[])

    class Meta:
        model = Eixo
        exclude = ()

    def __init__(self, *args, **kwargs):
        super(EixoForm, self).__init__(*args, **kwargs)

        ordem_choices = []
        qtd_eixos = Eixo.objects.count()

        for ordem in range(1, qtd_eixos + 2):
            ordem_choices.append([ordem, ordem])

        self.fields['ordem'].choices = ordem_choices

    def save(self, *args, **kwargs):
        if self.instance.ordem < Eixo.objects.count():
            qs = Eixo.objects.exclude(pk=self.instance.pk).filter(ordem__gte=self.instance.ordem).order_by('ordem')
            range_ordem = list(range(self.instance.ordem + 1, Eixo.objects.count() + 1))
        else:
            qs = Eixo.objects.exclude(pk=self.instance.pk).filter(ordem__lte=self.instance.ordem).order_by('ordem')
            range_ordem = list(range(1, self.instance.ordem + 1))

        for index, obj in enumerate(qs):
            obj.ordem = range_ordem[index]
            obj.save()

        return super(EixoForm, self).save(*args, **kwargs)


class IndicadorForm(forms.ModelFormPlus):
    anos_referencia = forms.ModelMultipleChoiceField(
        Ano.objects, label='Anos de Referência', required=True, widget=forms.widgets.CheckboxSelectMultiple()
    )
    macroprocesso = forms.ModelChoiceFieldPlus(Macroprocesso.objects)
    subsidio_para = forms.ModelMultipleChoiceField(TipoAvaliacao.objects, label='Subsídio p/ Avaliações', required=True, widget=forms.widgets.CheckboxSelectMultiple())
    segmentos = forms.MultipleModelChoiceFieldPlus(Segmento.objects, label='Segmentos', required=True, widget=FilteredSelectMultiplePlus('', True))
    uos = forms.ModelMultiplePopupChoiceField(
        UnidadeOrganizacional.objects.suap(), label='Campi', required=False, help_text='Caso se aplique a todos os campi pode deixar em branco'
    )
    areas_vinculacao = forms.ModelMultiplePopupChoiceField(AreaVinculacao.objects, label='Áreas', required=False)
    modalidades = forms.ModelMultiplePopupChoiceField(Modalidade.objects, label='Modalidades', required=False)

    fieldsets = (
        (
            'Dados Gerais',
            {
                'fields': (
                    'anos_referencia',
                    'macroprocesso',
                    'nome',
                    'texto_ajuda',
                    'aspecto',
                    'subsidio_para',
                    ('tipo', 'em_uso', 'automatico', 'obrigatorio', 'gestor_responde_como_docente'),
                )
            },
        ),
        ('Unidades Relacionadas', {'fields': (('envolve_reitoria', 'envolve_campus_ead'), ('envolve_campus_produtivos', 'envolve_campus_nao_produtivos'))}),
        ('Respondentes', {'fields': ('segmentos', 'uos')}),
        ('Qualificação dos Respondentes', {'fields': ('areas_vinculacao', 'modalidades', 'periodo_curso')}),
        ('Configuração de Resposta', {'fields': ('tipo_resposta', ('valor_minimo', 'valor_maximo'), 'formula')}),
    )

    class Meta:
        model = Indicador
        exclude = ()

    class Media:
        js = ('/static/avaliacao_integrada/js/IndicadorForm.js',)

    def __init__(self, *args, **kwargs):
        super(IndicadorForm, self).__init__(*args, **kwargs)
        areas_vinculacao_padrao = ['Ensino', 'Extensão', 'Pesquisa e Inovação', 'Atividades Estudantis']
        self.fields['areas_vinculacao'].initial = AreaVinculacao.objects.filter(descricao__in=areas_vinculacao_padrao).values_list('id', flat=True)
        self.fields['modalidades'].initial = Modalidade.objects.filter(
            pk__in=[Modalidade.TECNOLOGIA, Modalidade.LICENCIATURA, Modalidade.INTEGRADO, Modalidade.INTEGRADO_EJA, Modalidade.SUBSEQUENTE, Modalidade.CONCOMITANTE]
        )
        self.fields['tipo_resposta'].initial = Indicador.FAIXA_NUMERICA
        self.fields['anos_referencia'].queryset = Ano.objects.filter(ano__gte=2015, ano__lte=datetime.date.today().year)

    def clean_formula(self):
        if self.cleaned_data.get('tipo_resposta', None) == Indicador.CONJUNTO_VARIAVEIS:
            if not self.cleaned_data.get('formula', None):
                raise forms.ValidationError('A fórmula é obrigatória para respostas contendo variáveis.')
        return self.cleaned_data['formula']

    def clean(self):
        super(IndicadorForm, self).clean()

        if self.cleaned_data.get('automatico') and not self.cleaned_data.get('nome') in Indicador.INDICADORES_AUTOCALCULADOS:
            self.add_error('nome', 'O indicador informado não consta na lista de indicadores autocalculados esperados pelo sistema.')
        return self.cleaned_data


class AvaliacaoForm(forms.ModelFormPlus):
    tipos = forms.MultipleModelChoiceField(TipoAvaliacao.objects, label='Tipos', widget=forms.widgets.CheckboxSelectMultiple())
    areas_vinculacao = forms.ModelMultiplePopupChoiceField(AreaVinculacao.objects, label='Áreas', required=False)
    segmentos = forms.MultipleModelChoiceFieldPlus(Segmento.objects, label='Segmentos', required=False, widget=FilteredSelectMultiplePlus('', True))
    modalidades = forms.ModelMultiplePopupChoiceField(Modalidade.objects, label='Modalidades', required=False)
    uos = forms.ModelMultiplePopupChoiceField(UnidadeOrganizacional.objects.suap(), label='Campi', required=False)
    token = forms.CharFieldPlus(required=True, label='Token de Acesso')

    fieldsets = (
        ('Dados Gerais', {'fields': ('tipos', ('ano', 'periodo'), 'nome', 'descricao', ('data_inicio', 'data_termino'))}),
        ('Unidades Relacionadas', {'fields': (('envolve_reitoria', 'envolve_campus_ead', 'envolve_campus_produtivos', 'envolve_campus_nao_produtivos'),)}),
        ('Respondentes', {'fields': ('segmentos',)}),
        ('Qualificação dos Respondentes', {'fields': ('areas_vinculacao', 'modalidades', 'uos')}),
        ('Acesso à Avaliação Externa', {'fields': ('token',)}),
    )

    def clean_token(self):
        if Avaliacao.objects.exclude(pk=self.instance.pk).filter(token=self.cleaned_data.get('token')).exists():
            raise forms.ValidationError('O Token de Acesso informado já foi utilizado em outra Avaliação.')
        return self.cleaned_data.get('token')

    def __init__(self, *args, **kwargs):
        super(AvaliacaoForm, self).__init__(*args, **kwargs)

        if not self.instance.pk:
            self.fields['token'].initial = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(6))

    class Meta:
        model = Avaliacao
        exclude = ()


class AvaliacaoExternaForm(forms.FormPlus):
    SUBMIT_LABEL = 'Acessar'
    token = forms.CharFieldPlus(required=True, label='Token de Acesso')
    tipo_respondente = forms.ChoiceField(
        choices=[[Segmento.PAIS, 'Pais'], [Segmento.EMPRESAS, 'Empresas'], [Segmento.SOCIEDADE_CIVIL, 'Sociedade Civil'], [Segmento.DESLIGADO, 'Evadidos/Jubilados']],
        label='Tipo do Respondente',
    )
    recaptcha = ReCaptchaField(label='')


class RelatorioForm(forms.Form):
    METHOD = 'get'

    avaliacao = forms.ModelChoiceField(Avaliacao.objects, label='Avaliação', required=True)
    tipos = forms.ModelMultipleChoiceField(TipoAvaliacao.objects, label='Tipos', required=False, widget=forms.CheckboxSelectMultiple())

    def __init__(self, *args, **kwargs):
        super(RelatorioForm, self).__init__(*args, **kwargs)

        self.fieldsets = [('Avaliação', {'fields': ('ano', 'avaliacao')}), ('Tipos de Avaliação', {'fields': ('tipos',)})]

    def processar(self):
        qs = Indicador.objects.all()
        avaliacao = self.cleaned_data.get('avaliacao')
        tipos = self.cleaned_data.get('tipos')

        if avaliacao or tipos:
            qs_resposta = Resposta.objects.all()
            if avaliacao:
                qs_resposta = qs_resposta.filter(respondente__avaliacao=avaliacao)
            if tipos:
                qs_resposta = qs_resposta.filter(indicador__subsidio_para__in=tipos)

            ids = qs_resposta.values_list('indicador', flat=True).order_by('indicador').distinct()
            qs = qs.filter(id__in=ids)

        qs = qs.distinct()
        return qs


class RelatorioXLSXForm(forms.Form):
    METHOD = 'get'

    avaliacao = forms.ModelChoiceField(Avaliacao.objects, label='Avaliação', required=False)
    eixo = forms.ModelChoiceField(Eixo.objects, label='Eixo', required=False)
    dimensao = forms.ModelChoiceField(Dimensao.objects, label='Dimensão', required=False)
    macroprocesso = forms.ModelChoiceField(Macroprocesso.objects, label='Macroprocesso', required=False)
    segmentos = forms.ModelMultiplePopupChoiceField(Segmento.objects, required=False)
    areas_vinculacao = forms.ModelMultiplePopupChoiceField(AreaVinculacao.objects, label='Áreas', required=False)
    uos = forms.ModelMultiplePopupChoiceField(UnidadeOrganizacional.objects.suap(), label='Campi', required=False)
    modalidades = forms.ModelMultiplePopupChoiceField(Modalidade.objects, label='Modalidades', required=False)
    cursos = forms.MultipleModelChoiceFieldPlus(CursoCampus.objects, label='Cursos', required=False)
    tipos = forms.ModelMultiplePopupChoiceField(TipoAvaliacao.objects, label='Tipos', required=False)

    def processar(self):
        avaliacao = self.cleaned_data.get('avaliacao')
        eixo = self.cleaned_data.get('eixo')
        dimensao = self.cleaned_data.get('dimensao')
        macroprocesso = self.cleaned_data.get('macroprocesso')
        segmentos = self.cleaned_data.get('segmentos')
        areas_vinculacao = self.cleaned_data.get('areas_vinculacao')
        uos = self.cleaned_data.get('uos')
        modalidades = self.cleaned_data.get('modalidades')
        cursos = self.cleaned_data.get('cursos')
        tipos = self.cleaned_data.get('tipos')

        respostas = Resposta.objects.all()

        if avaliacao:
            respostas = respostas.filter(respondente__avaliacao=avaliacao)
        if eixo:
            respostas = respostas.filter(indicador__macroprocesso__dimensao__eixo=eixo)
        if dimensao:
            respostas = respostas.filter(indicador__macroprocesso__dimensao=dimensao)
        if macroprocesso:
            respostas = respostas.filter(indicador__macroprocesso=macroprocesso)
        if segmentos:
            respostas = respostas.filter(respondente__segmento__in=segmentos)
        if areas_vinculacao:
            respostas = respostas.exclude(respondente__segmento__in=Segmento.SERVIDORES) | respostas.filter(
                respondente__segmento__in=Segmento.SERVIDORES, respondente__user__vinculo__setor__areas_vinculacao__in=areas_vinculacao.values_list('id', flat=True)
            )
        if uos:
            respostas = (
                respostas.exclude(respondente__segmento__in=Segmento.SERVIDORES + Segmento.ALUNOS)
                | respostas.filter(respondente__segmento__in=Segmento.SERVIDORES, respondente__uo__in=uos.values_list('id', flat=True))
                | respostas.filter(respondente__segmento__in=Segmento.ALUNOS, respondente__uo__in=uos.values_list('id', flat=True))
            )
        if modalidades:
            respostas = respostas.exclude(respondente__segmento__in=Segmento.ALUNOS) | respostas.filter(
                respondente__segmento__in=Segmento.ALUNOS, respondente__user__pessoafisica__aluno_edu_set__curso_campus__modalidade__in=modalidades.values_list('id', flat=True)
            )
        if cursos:
            respostas = respostas.exclude(respondente__segmento__in=Segmento.ALUNOS) | respostas.filter(
                respondente__segmento__in=Segmento.ALUNOS, respondente__user__pessoafisica__aluno_edu_set__curso_campus__in=cursos.values_list('id', flat=True)
            )
        if tipos:
            respostas = respostas.filter(indicador__subsidio_para__in=tipos)

        return (
            respostas.select_related(
                'indicador', 'indicador__macroprocesso__dimensao__eixo', 'indicador__macroprocesso__dimensao', 'indicador__macroprocesso', 'respondente', 'respondente__segmento'
            )
            .order_by('respondente')
            .distinct()
        )


class FiltroIndicadorForm(forms.Form):
    SUBMIT_LABEL = 'Filtrar'

    segmentos = forms.MultipleModelChoiceField(Segmento.objects, required=False, widget=forms.CheckboxSelectMultiple())
    areas_vinculacao = forms.ModelMultiplePopupChoiceField(AreaVinculacao.objects, label='Áreas', required=False)
    uos = forms.ModelMultiplePopupChoiceField(UnidadeOrganizacional.objects.suap(), label='Campi', required=False)
    modalidades = forms.ModelMultiplePopupChoiceField(Modalidade.objects, label='Modalidades', required=False)
    cursos = forms.MultipleModelChoiceFieldPlus(CursoCampus.objects, label='Cursos', required=False)

    def filtrar_respostas(self, respostas):
        segmentos = self.cleaned_data['segmentos']
        areas_vinculacao = self.cleaned_data['areas_vinculacao']
        uos = self.cleaned_data['uos']
        modalidades = self.cleaned_data['modalidades']
        cursos = self.cleaned_data['cursos']
        return FiltroIndicadorForm.filtrar_respostas2(respostas, segmentos, areas_vinculacao, uos, modalidades, cursos)

    @staticmethod
    def filtrar_respostas2(respostas, segmentos=None, areas_vinculacao=None, uos=None, modalidades=None, cursos=None):

        if segmentos is not None and segmentos.exists():
            respostas = respostas.filter(respondente__segmento__in=segmentos)

        if areas_vinculacao is not None and areas_vinculacao.exists():
            respostas = respostas.exclude(respondente__segmento__in=Segmento.SERVIDORES) | respostas.filter(
                respondente__segmento__in=Segmento.SERVIDORES, respondente__user__vinculo__setor__areas_vinculacao__in=areas_vinculacao.values_list('id', flat=True)
            )

        if uos is not None and uos.exists():
            respostas = (
                respostas.exclude(respondente__segmento__in=Segmento.SERVIDORES + Segmento.ALUNOS)
                | respostas.filter(respondente__segmento__in=Segmento.SERVIDORES, respondente__uo__in=uos.values_list('id', flat=True))
                | respostas.filter(respondente__segmento__in=Segmento.ALUNOS, respondente__uo__in=uos.values_list('id', flat=True))
            )

        if modalidades is not None and modalidades.exists():
            respostas = respostas.exclude(respondente__segmento__in=Segmento.ALUNOS) | respostas.filter(
                respondente__segmento__in=Segmento.ALUNOS, respondente__user__pessoafisica__aluno_edu_set__curso_campus__modalidade__in=modalidades.values_list('id', flat=True)
            )
        if cursos is not None and cursos.exists():
            respostas = respostas.exclude(respondente__segmento__in=Segmento.ALUNOS) | respostas.filter(
                respondente__segmento__in=Segmento.ALUNOS, respondente__user__pessoafisica__aluno_edu_set__curso_campus__in=cursos.values_list('id', flat=True)
            )

        return respostas.order_by('respondente').distinct()

    def filtrar_respondentes(self, respondentes):

        segmentos = self.cleaned_data['segmentos']
        areas_vinculacao = self.cleaned_data['areas_vinculacao']
        uos = self.cleaned_data['uos']
        modalidades = self.cleaned_data['modalidades']
        cursos = self.cleaned_data['cursos']
        return self.filtrar_respondentes2(respondentes, segmentos, areas_vinculacao, uos, modalidades, cursos)

    @staticmethod
    def filtrar_respondentes2(respondentes, segmentos=None, areas_vinculacao=None, uos=None, modalidades=None, cursos=None):
        if segmentos is not None and segmentos.exists():
            respondentes = respondentes.filter(segmento__in=segmentos)

        if areas_vinculacao is not None and areas_vinculacao.exists():
            respondentes = respondentes.exclude(segmento__in=Segmento.SERVIDORES) | respondentes.filter(
                segmento__in=Segmento.SERVIDORES, user__vinculo__setor__areas_vinculacao__in=areas_vinculacao.values_list('id', flat=True)
            )

        if uos is not None and uos.exists():
            respondentes = (
                respondentes.exclude(segmento__in=Segmento.SERVIDORES + Segmento.ALUNOS + Segmento.EXTERNOS)
                | respondentes.filter(segmento__in=Segmento.SERVIDORES, uo__in=uos.values_list('id', flat=True))
                | respondentes.filter(segmento__in=Segmento.ALUNOS, uo__in=uos.values_list('id', flat=True))
            )

        if modalidades is not None and modalidades.exists():
            respondentes = respondentes.exclude(segmento__in=Segmento.ALUNOS) | respondentes.filter(
                segmento__in=Segmento.ALUNOS, user__pessoafisica__aluno_edu_set__curso_campus__modalidade__in=modalidades.values_list('id', flat=True)
            )

        if cursos is not None and cursos.exists():
            respondentes = respondentes.exclude(segmento__in=Segmento.ALUNOS) | respondentes.filter(
                segmento__in=Segmento.ALUNOS, user__pessoafisica__aluno_edu_set__curso_campus__in=cursos.values_list('id', flat=True)
            )

        return respondentes.distinct()
