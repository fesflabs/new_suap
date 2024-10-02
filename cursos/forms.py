# -*- coding: utf-8 -*-

from datetime import datetime
from threading import Thread

from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms.widgets import Select

from comum.models import Ano
from cursos.enums import SituacaoCurso, SituacaoParticipante
from cursos.models import Curso, Atividade, Participante, CotaExtra
from djtools import forms
from djtools.choices import Meses
from djtools.forms.widgets import AutocompleteWidget
from djtools.utils import send_notification
from protocolo.models import Processo
from rh.models import UnidadeOrganizacional, Servidor


class CursoForm(forms.ModelFormPlus):
    descricao = forms.CharField(label='Descrição', widget=forms.Textarea(attrs={'rows': '2', 'columns': '40'}))
    processos = forms.MultipleModelChoiceFieldPlus(
        label='Processos relacionados', required=False, queryset=Processo.objects.all()
    )

    responsaveis = forms.MultipleModelChoiceFieldPlus(
        label='Responsáveis', required=False, queryset=Servidor.objects.ativos())

    campus = forms.ModelChoiceField(required=True, label='Unidade Organizacional', queryset=UnidadeOrganizacional.objects.suap().all())

    situacao = forms.ChoiceField(choices=[], required=False, label='Situação')

    fieldsets = ((None, {'fields': ('descricao', 'ano_pagamento', 'campus', 'participantes', 'tipo', 'edital', 'processos')}),)

    class Meta:
        model = Curso
        exclude = ()

    def __init__(self, *args, **kwargs):
        super(CursoForm, self).__init__(*args, **kwargs)

        lista_situacao_choices = []
        for k, v in SituacaoCurso.get_choices():
            if k == SituacaoCurso.FINALIZADO:
                continue
            lista_situacao_choices.append([k, v])
        self.fields['situacao'].choices = lista_situacao_choices

        if 'instance' in kwargs:
            atributo_edital = self.instance.edital
            self.fields['situacao'].initial = SituacaoCurso.NAO_INICIADO
            try:
                atributo_processos = self.instance.processos.all()
            except Exception:
                atributo_processos = None
            if atributo_edital:
                self.fields['edital'].help_text = '<a href="{}">Clique para ver edital</a>'.format(atributo_edital.url)
            else:
                self.fields['edital'].help_text = 'Não há edital cadastrado'
            if atributo_processos:
                retorno = ''
                for p in atributo_processos:
                    retorno = retorno + '<a href="{}">Clique para ver processo {}</a>'.format(p.get_absolute_url(), p.__str__())
                    retorno = retorno + '<br / >'
                self.fields['processos'].help_text = retorno
            else:
                self.fields['processos'].help_text = 'Não há processos relacionados.'

    def clean_situacao(self):
        situacao = self.cleaned_data.get('situacao')
        if situacao:
            situacao = int(situacao)

            curso = self.instance
            qs_participantes = curso.participante_set

            if situacao != SituacaoCurso.NAO_INICIADO and not qs_participantes.exists():
                raise ValidationError('Você não pode mudar a situação do evento enquanto não existir pelo menos um participante cadastrado.')

            if situacao == SituacaoCurso.INICIADO and (self.instance.tem_participante_problema_horas() or self.instance.tem_participante_aguardando_liberacao):
                raise ValidationError('O evento não pode ser iniciado pois existem participantes com problemas de carga horária ou aguardando liberação da chefia imediata.')

            if (situacao == SituacaoCurso.FINALIZADO or situacao == SituacaoCurso.AGUARDANDO_CADASTRO_EM_FOLHA) and self.instance.tem_participante_sem_hora_trabalhada:
                raise ValidationError('O evento não pode ser finalizado pois existem participantes sem hora trabalhada cadastrada.')

            if situacao == SituacaoCurso.CADASTRADO_EM_FOLHA and not self.instance.situacao == situacao:
                self.instance.informar_cadastro_folha(self.request)

        return situacao


class AtividadeForm(forms.ModelFormPlus):
    valor_hora = forms.DecimalFieldPlus(label='Valor da Hora')

    class Meta:
        model = Atividade
        exclude = ()


class ParticipanteForm(forms.ModelFormPlus):
    atividade = forms.ModelChoiceFieldPlus(Atividade.objects)
    atividade_mes = forms.ChoiceField(choices=Meses.get_choices(), label='Mês da Atividade')

    def __init__(self, *args, **kwargs):
        curso_concurso = kwargs.pop('curso', None)
        super(ParticipanteForm, self).__init__(*args, **kwargs)

        if self.instance and self.instance.id:
            self.fields['servidor'].widget = forms.HiddenInput()

        if curso_concurso:
            self.fields['curso'].initial = curso_concurso.id
        self.fields['curso'].widget = forms.HiddenInput()

        self.fields['atividade'].queryset = Atividade.objects.filter(ativa=True)

        mes_atual = datetime.now().month
        self.fields['atividade_mes'].initial = mes_atual

    class Meta:
        model = Participante
        exclude = ('mes_pagamento', 'horas_trabalhada', 'motivo_nao_liberacao', 'situacao', 'responsavel_liberacao', 'data_liberacao')

    def clean(self):
        servidor = self.cleaned_data.get('servidor')
        curso = self.cleaned_data.get('curso')
        atividade = self.cleaned_data.get('atividade')
        atividade_mes = self.cleaned_data.get('atividade_mes')
        '''
        Condições para verificar se o servidor já está participando do evento
          1 - o servidor deve estar setado
          2 - o curso deve estar setado
          3 - a instância não deve ter id, essa verificação deve ser feita apenas no cadastro
        '''
        if servidor and curso and self.instance.id is None:
            # verificando se o servidor já está cadastrado para o evento/atividade
            if curso.participante_set.filter(servidor=servidor, atividade=atividade, atividade_mes=atividade_mes).exists():
                raise ValidationError('O servidor {} já está participando desta atividade no mesmo mês.'.format(servidor))
        return self.cleaned_data

    def save(self, commit=True):
        if self.instance and self.instance.id:
            participante = Participante.objects.get(id=self.instance.id)
            # se a hora prevista for alterada, a chefia deve avaliar novamente
            if participante.horas_prevista != self.instance.horas_prevista:
                self.instance.situacao = SituacaoParticipante.AGUARDANDO_LIBERACAO
        super(ParticipanteForm, self).save()

        t1 = Thread(self._email_para_chefe_imediato(self.instance))
        t1.start()

    def _email_para_chefe_imediato(self, instance):
        if instance:
            url = '{}/admin/cursos/participante/'.format(settings.SITE_URL)
            titulo = '[SUAP] GECC: Participação em Curso/Concurso'
            texto = (
                '<h1>GECC: Participação em Curso/Concurso</h1>'
                '<h2>Pedido de vista à chefia imediata</h2>'
                '<p>O servidor {} foi selecionado para participar do curso/concurso {}.</p>'
                '<p>No entanto, é necessário um parecer da chefia imediata, deferindo ou indeferindo a participação do servidor no evento.</p>'
                '<p>Para avaliar a participação do servidor, basta entrar no SUAP e acessar o menu <a href="{}">Gestão de Pessoas -> Desenvolvimento de Pessoal -> Cursos '
                'e Concursos -> Participantes</a>. Você também receberá um alerta na página inicial do SUAP caso tenho solicitações pendentes.</p>'.format(
                    instance.servidor.nome, instance.curso.descricao, url
                )
            )

            vinculos = []
            for i in instance.servidor.chefes_imediatos():  # chefes_imediatos() devolve um queryset de servidor
                vinculos.append(i.get_vinculo())
            send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, vinculos)


class AdicionarHorasTrabalhadasForm(forms.ModelFormPlus):
    # ano_desconto_carga_horaria = forms.ChoiceField(label=u'Ano Carga Horária', required=True)

    def __init__(self, *args, **kwargs):
        super(AdicionarHorasTrabalhadasForm, self).__init__(*args, **kwargs)
        if self.instance:
            self.fields['servidor'].widget = forms.HiddenInput()
            self.fields['servidor'].initial = self.instance.servidor.id

        # ano_atual = datetime.now().year
        # self.fields['ano_desconto_carga_horaria'].choices = [[ano_atual-1, ano_atual-1], [ano_atual, ano_atual], [ano_atual+1, ano_atual+1]]
        # self.fields['ano_desconto_carga_horaria'].initial = ano_atual

    class Meta:
        model = Participante
        # fields = ('horas_trabalhada', 'ano_desconto_carga_horaria', 'servidor')
        fields = ('horas_trabalhada', 'servidor')

    def clean_horas_trabalhada(self):
        horas_trabalhada = self.cleaned_data.get('horas_trabalhada')
        if horas_trabalhada is None:
            raise ValidationError('Informe a quantidade de horas trabalhadas.')
        participante = self.instance
        horas_disponiveis = participante.horas_disponiveis_ano + participante.horas_prevista

        # verificando horas disponíveis para o servidor
        if horas_disponiveis < horas_trabalhada:
            raise ValidationError(
                'Não é possível adicionar a quantidade de {} horas trabalhadas, pois o servidor dispoem apenas de {} horas.'.format(horas_trabalhada, horas_disponiveis)
            )

        return horas_trabalhada


class CotaExtraForm(forms.ModelFormPlus):
    servidor = forms.ModelChoiceFieldPlus(Servidor.objects, widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS))
    ano = forms.ModelChoiceFieldPlus(Ano.objects, widget=Select())
    processos = forms.MultipleModelChoiceFieldPlus(Processo.objects, required=True)

    class Meta:
        model = CotaExtra
        exclude = ('data_cadastro',)

    def clean_horas_permitida(self):
        horas_permitidas = self.cleaned_data.get('horas_permitida')
        servidor = self.cleaned_data.get('servidor')
        ano = self.cleaned_data.get('ano')

        if horas_permitidas > Participante.VALOR_PADRAO_HORAS_TRABALHADAS:
            raise ValidationError('O máximo de horas permitidas para cota extra é de 120 horas.')

        # verificando as cotas já cadastradas para o servidor no ano em questão
        saldo_cadastrado = CotaExtra.cota_extra_servidor_no_ano(servidor, ano)

        saldo_total = saldo_cadastrado + horas_permitidas
        if saldo_total > Participante.VALOR_PADRAO_HORAS_TRABALHADAS:
            raise ValidationError('A cota extra total ({}) do servidor ultrapassa o limite máximo de {}.'.format(saldo_total, Participante.VALOR_PADRAO_HORAS_TRABALHADAS))

        return horas_permitidas


class IndeferimentoParticipanteForm(forms.FormPlus):
    motivo = forms.CharFieldPlus(label='Motivo Indeferimento', max_length=500)
    participante = forms.ModelChoiceFieldPlus(queryset=Participante.objects)

    def __init__(self, *args, **kwargs):
        participante = kwargs.pop('participante', None)
        super(IndeferimentoParticipanteForm, self).__init__(*args, **kwargs)

        self.fields['participante'].widget = forms.HiddenInput()
        self.fields['participante'].initial = participante.id

        self.fields['motivo'].widget = forms.Textarea()

    def processar(self):
        participante = self.cleaned_data.get('participante')
        participante.indeferir_participacao(self.cleaned_data.get('motivo'))

        # email
        titulo = '[SUAP] GECC: Participação em Curso/Concurso'
        texto = (
            '<h1>GECC: Participação em Curso/Concurso</h1>'
            '<h2>Participação indeferida pela chefia imediata</h2>'
            '<p>{},</p>'
            '<p>Sua participação em <strong>{}</strong> foi indeferida pela chefia imediata.</p>'
            '<p>--</p>'
            '<dl><dt>Motivo do Indeferimento:</dt><dd>{}</dd></dl>'.format(participante.servidor.nome, participante.curso.descricao, self.cleaned_data.get('motivo'))
        )

        t1 = Thread(send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [participante.servidor.get_vinculo()]))
        t1.start()


class RelatorioFinanceiroPagamentoGECCForm(forms.FormPlus):
    ano = forms.ModelChoiceFieldPlus(Ano.objects, widget=Select(), label='Ano')
    mes = forms.ChoiceField(choices=Meses.get_choices(), label='Mês')


class CotaAnualServidorGECCForm(forms.FormPlus):
    METHOD = 'GET'
    texto_busca = forms.CharFieldPlus(label='Texto', required=False, help_text='Apenas o nome do servidor.')
    ano = forms.ModelChoiceFieldPlus(Ano.objects, widget=Select(), label='Ano', required=False)

    fieldsets = ((None, {'fields': ('texto_busca', 'ano')}),)


class EditarMesPagamentoGECCForm(forms.FormPlus):
    participante = forms.ModelChoiceFieldPlus(queryset=Participante.objects)
    mes = forms.ChoiceField(choices=Meses.get_choices(), label='Mês')

    def __init__(self, *args, **kwargs):
        participante = kwargs.pop('participante', None)
        super(EditarMesPagamentoGECCForm, self).__init__(*args, **kwargs)

        self.fields['participante'].widget = forms.HiddenInput()
        self.fields['participante'].initial = participante.id

        if participante:
            self.fields['mes'].initial = participante.mes_pagamento

    def processar(self):
        participante = self.cleaned_data.get('participante')
        mes = self.cleaned_data.get('mes')
        participante.mes_pagamento = mes
        participante.save()


class FiltroPendentesPagamentoForm(forms.FormPlus):
    METHOD = 'GET'
    participante = forms.CharFieldPlus(label='Nome do Participante', required=False)
    evento = forms.ChoiceField(choices=[], label='Evento', required=False)

    def __init__(self, *args, **kwargs):
        super(FiltroPendentesPagamentoForm, self).__init__(*args, **kwargs)

        lista = [['', '-- Selecione --']]
        for i in Curso.objects.filter(participante__situacao=SituacaoParticipante.PENDENTE).distinct():
            lista.append([i.id, i.descricao])
        self.fields['evento'].choices = lista
