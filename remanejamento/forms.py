# -*- coding: utf-8 -*-

from django.apps import apps
from django.utils.safestring import mark_safe

from comum.models import User
from djtools import forms
from djtools.forms.widgets import AutocompleteWidget, FilteredSelectMultiplePlus
from djtools.utils import to_ascii
from edu.models import Disciplina as DisciplinaEdu
from remanejamento.models import Disciplina, DisciplinaItem, Edital, EditalRecurso, Inscricao, InscricaoDisciplinaItem, \
    InscricaoItem
from rh.models import CargoEmprego, UnidadeOrganizacional


class EditalRecursoForm(forms.FormPlus):
    edital = forms.ModelChoiceField(label='Edital', queryset=Edital.objects.all(), widget=AutocompleteWidget(readonly=True))
    recurso_texto = forms.CharField(
        label="Recurso",
        widget=forms.Textarea(attrs={'rows': '50', 'cols': '100'}),
        help_text='A resposta a este recurso poderá '
        'ser acompanhada clicando no menu "Gestão de Pessoas -> Remanejamento -> '
        'Recursos ao Edital" na data/hora informada no Edital.',
    )

    def __init__(self, *args, **kwargs):
        if 'id_edital' in kwargs:
            edital_id = kwargs.pop('id_edital')
            super(EditalRecursoForm, self).__init__(*args, **kwargs)
            self.fields['edital'].initial = edital_id


class EditalRecursoRespostaForm(forms.ModelFormPlus):
    SUBMIT_LABEL = "Enviar"
    recurso_resposta = forms.CharField(label="Resposta", widget=forms.Textarea(attrs={'rows': '50', 'cols': '100'}))

    class Meta:
        model = EditalRecurso
        fields = ('recurso_resposta',)


class DisciplinaForm(forms.FormPlus):
    edital = forms.ModelChoiceField(label='Edital', queryset=Edital.objects.all(), widget=AutocompleteWidget(readonly=True))
    disciplinas = forms.ModelMultipleChoiceField(
        queryset=DisciplinaEdu.objects.all(),
        label='Disciplinas',
        widget=FilteredSelectMultiplePlus('', True),
        required=True,
        help_text="Escolha as disciplinas referentes ao edital",
    )

    def __init__(self, *args, **kwargs):
        if 'id_edital' in kwargs:
            edital_id = kwargs.pop('id_edital')
            super(DisciplinaForm, self).__init__(*args, **kwargs)
            edital = Edital.objects.get(pk=edital_id)
            self.fields['edital'].initial = edital.id


class DisciplinaItemForm(forms.FormPlus):
    conteudo = forms.CharField(label='Conteúdo', widget=forms.Textarea(attrs={'rows': '50', 'cols': '100'}), help_text='disciplina|sequencia|item')

    def save(self, edital):
        def formatar(valor):
            return to_ascii(valor.strip().upper())

        # Indexando as disciplinas por descricao formatada
        edital_disciplinas = dict()
        for d in edital.disciplina_set.all():
            edital_disciplinas[formatar(d.descricao)] = d

        conteudo = self.cleaned_data['conteudo']
        for linha in conteudo.split('\n'):
            disciplina_descricao, item_sequencia, item_descricao = linha.split('|')
            disciplina_descricao_formatada = formatar(disciplina_descricao)
            if disciplina_descricao_formatada in edital_disciplinas:
                disciplina = edital_disciplinas[disciplina_descricao_formatada]
                DisciplinaItem.objects.create(disciplina=disciplina, descricao=item_descricao, sequencia=int(item_sequencia))
            else:
                print(('Disciplina nao encontrada: %s' % disciplina_descricao_formatada))


def CoordenadorInscricaoEditarFormFactory(inscricao):
    """Form para o coordenador definir o avaliador e o status da inscrição"""

    class CoordenadorInscricaoEditarForm(forms.ModelFormPlus):
        class Meta:
            model = Inscricao
            fields = ('avaliacao_avaliador', 'avaliacao_status')

        avaliacao_avaliador = forms.ModelChoiceField(
            queryset=inscricao.disciplina.avaliadores.all(),
            required=False,
            label='Avaliador',
            help_text='Só poderá ser escolhido usuário avaliador da disciplina '
            '<a href="/admin/remanejamento/disciplina/%d/">%s</a>.' % (inscricao.disciplina.pk, inscricao.disciplina.descricao),
        )

    return CoordenadorInscricaoEditarForm


def AvaliadorInscricaoFormFactory(inscricao):
    """Form para o avaliador definir a aptidão para cada item de disciplina"""
    CHOICE_PERCENTUAL = ((0, '0%'), (10, '10%'), (20, '20%'), (30, '30%'), (40, '40%'), (50, '50%'), (60, '60%'), (70, '70%'), (80, '80%'), (90, '90%'), (100, '100%'))
    CHOICE_PADRAO = ((0, '-'),)

    class AvaliadorInscricaoForm(forms.FormPlus):

        SUBMIT_LABEL = 'Avaliar Inscrição'

        def save(self):
            inscricao.observacao = self.cleaned_data['observacao']
            inscricao.avaliacao_recurso = self.cleaned_data['avaliacao_recurso']
            inscricao.save()
            for key, val in list(self.cleaned_data.items()):
                if not key.startswith('di_'):
                    continue
                idi, created = InscricaoDisciplinaItem.objects.get_or_create(inscricao=inscricao, disciplina_item=DisciplinaItem.objects.get(pk=key.split('_')[-1]))
                idi.apto_percentual = val
                idi.save()
            inscricao.atualizar_score()
            inscricao.avaliacao_status = 'Avaliado'
            inscricao.save()

    for di in inscricao.disciplina.disciplinaitem_set.all():
        try:
            initial = InscricaoDisciplinaItem.objects.get(inscricao=inscricao, disciplina_item=di).apto_percentual

        except Exception:
            initial = 0

        if di.nao_avaliar:
            AvaliadorInscricaoForm.base_fields['dh_%d' % di.pk] = forms.IntegerField(
                label=mark_safe("<strong>%s</strong>" % di.descricao), required=False, initial='-', widget=forms.Select(choices=CHOICE_PADRAO, attrs={"disabled": "disabled"})
            )
        else:
            AvaliadorInscricaoForm.base_fields['di_%d' % di.pk] = forms.IntegerField(
                label=di.descricao, required=False, initial=initial, widget=forms.Select(choices=CHOICE_PERCENTUAL)
            )

    AvaliadorInscricaoForm.base_fields['observacao'] = forms.CharField(
        widget=forms.Textarea(), required=False, label='Observações (Os itens não aptos devem ser explicados aqui)', initial=inscricao.observacao
    )

    AvaliadorInscricaoForm.base_fields['avaliacao_recurso'] = forms.CharField(
        widget=forms.Textarea(), required=False, label='Avaliação do recurso', initial=inscricao.avaliacao_recurso
    )

    return AvaliadorInscricaoForm


class DisciplinaAdminForm(forms.ModelFormPlus):
    class Meta:
        model = Disciplina
        exclude = ()

    avaliadores = forms.MultipleModelChoiceFieldPlus(queryset=User.objects.order_by('username'), required=False)


class EditalForm(forms.ModelFormPlus):
    cargos = forms.MultipleModelChoiceFieldPlus(
        queryset=CargoEmprego.utilizados, help_text='Servidores destes cargos poderão se inscrever neste edital.'
    )

    coordenadores = forms.MultipleModelChoiceFieldPlus(
        required=False, queryset=User.objects.all(), help_text='Os coordenadores poderão acompanhar as inscrições deste edital.'
    )

    campus = forms.MultipleModelChoiceFieldPlus(label='Campi', queryset=UnidadeOrganizacional.objects.uo().all(), help_text='Informe os campi participantes deste remanejamento', widget=FilteredSelectMultiplePlus('', True), required=True)

    class Meta:
        model = Edital
        exclude = ()

    def clean_campus(self):
        campus = self.cleaned_data['campus']
        if campus.count() == 0:
            raise forms.ValidationError("Nenhum campus selecionado.")

        return campus


def InscreverFormFactory(edital, user):

    servidor = user.get_relacionamento()

    class InscricaoForm(forms.ModelFormPlus):
        class Meta:
            model = apps.get_model('remanejamento', 'inscricao')
            exclude = ['servidor', 'edital', 'frase_pura', 'frase_pura_com_chave', 'frase_hash', 'avaliacao_status', 'inicio_exercicio', 'jornada_trabalho']

    fieldsets = []

    # Disciplinas
    if edital.disciplina_set.count():
        InscricaoForm.base_fields['disciplina'] = forms.ModelChoiceField(queryset=edital.disciplina_set.all())
        InscricaoForm.base_fields['ingressou_na_disciplina'] = forms.BooleanField(
            required=False,
            help_text='Marque esse opção caso tenha ingressado na mesma disciplina informada acima.<br/>'
            'Em caso afirmativo, não é necessário anexar a documentação necessária abaixo.',
        )
        fieldsets += [('Escolha da disciplina', {'fields': (('disciplina',), ('ingressou_na_disciplina',))})]

    # Anexo
    if edital.tem_anexo:
        InscricaoForm.base_fields['anexo'] = forms.FileFieldPlus(
            help_text='Anexe aqui a documentação necessária conforme edital. (Tamanho máximo do arquivo: 50Mb)', required=False
        )
        fieldsets += [('Documentação necessária', {'fields': ('anexo',)})]

    # Tratando fields para campi
    campi_fields = []
    for campus in UnidadeOrganizacional.objects.suap().filter(pk__in=edital.campus.all().values_list('pk', flat=True)).order_by('setor__sigla'):
        field = forms.IntegerFieldPlus(required=False, label=campus.nome, widget=forms.NumberInput(attrs={'min': '1', 'step': '1'}))
        field_name = 'campus_' + str(campus.pk)
        campi_fields.append(field_name)
        InscricaoForm.base_fields[field_name] = field

    fieldsets += [
        ('Início de Exercício, Jornada de Trabalho e Classificação no Concurso', {'fields': ('inicio_exercicio', 'jornada_trabalho', 'classificacao_concurso')}),
        ('DOU do Edital de Homologação do Concurso Público para Ingresso na Instituição', {'fields': (('dou_numero', 'dou_data'), ('dou_pagina', 'dou_sessao'))}),
        ('Ordens de Preferência por Campus', {'fields': campi_fields}),
    ]
    InscricaoForm.fieldsets = fieldsets

    def clean(form):
        ordens_preferencia = []
        for key in campi_fields:
            ordens_preferencia.append(form.cleaned_data.get(key))
        for i in ordens_preferencia:
            if i is not None and ordens_preferencia.count(i) > 1:
                raise forms.ValidationError('As ordens de preferência dos campi devem ser únicas.')
        if list(set(ordens_preferencia)) == [None]:
            raise forms.ValidationError('Pelo menos uma ordem de preferência por campus deve ser escolhida')
        return form.cleaned_data

    def clean_anexo(self):
        if 'ingressou_na_disciplina' not in self.data:
            if not self.cleaned_data['anexo']:
                raise forms.ValidationError('Este campo é obrigatório.')
        if self.cleaned_data['anexo']:
            file_ = self.cleaned_data['anexo']
            # verfica se MIME TYPE é PDF ou Octet-Stream (devido bug no Firefox < v7), e se a extensão é .PDF
            if (('pdf' not in file_.content_type.lower()) and ('application/octet-stream' not in file_.content_type.lower())) or ((not file_.name.lower().endswith('.pdf'))):
                raise forms.ValidationError('O anexo deve estar no formato PDF (recebido: %s)' % file_.content_type)
            if file_.size > 52428800:  # 50Mb
                raise forms.ValidationError('O anexo deve ter no maximo 50MB')

        return self.cleaned_data['anexo']

    def save(form):
        if not edital.is_em_periodo_de_inscricao_servidor(servidor):
            raise Exception('Inscricoes fora do periodo')

        form.instance.edital = edital
        form.instance.servidor = servidor
        form.instance.jornada_trabalho = servidor.jornada_trabalho
        form.instance.inicio_exercicio = servidor.data_inicio_exercicio_no_cargo
        inscricao = super(InscricaoForm, form).save()
        for key in campi_fields:
            preferencia = form.cleaned_data[key]
            if not preferencia:
                continue
            campus_pk = int(key.split('_')[1])
            campus = UnidadeOrganizacional.objects.suap().get(pk=campus_pk)
            InscricaoItem.objects.create(inscricao=inscricao, campus=campus, preferencia=preferencia)
            inscricao.atualizar_frases()
        return inscricao

    InscricaoForm.clean = clean
    InscricaoForm.save = save
    if edital.tem_anexo:
        InscricaoForm.clean_anexo = clean_anexo

    return InscricaoForm


class InscricaoRecursoForm(forms.ModelFormPlus):
    SUBMIT_LABEL = "Enviar"

    class Meta:
        model = Inscricao
        fields = ['recurso_texto']


class InscricaoRespostaRecursoForm(forms.ModelFormPlus):
    SUBMIT_LABEL = "Enviar"

    class Meta:
        model = Inscricao
        fields = ['avaliacao_recurso']
