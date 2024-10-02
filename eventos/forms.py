from django.db.models.aggregates import Count
from django.db import transaction
from comum.utils import get_uo
from djtools import forms
from djtools.forms.fields import BrCpfField
from eventos.models import (
    Evento,
    Dimensao,
    SubtipoEvento,
    TipoEvento,
    ClassificacaoEvento,
    PublicoAlvoEvento,
    Participante,
    Banner,
    AtendimentoPublico,
    TipoParticipante,
    HistoricoEvento,
    TipoParticipacao,
    AnexoEvento,
    FotoEvento,
    AtividadeEvento,
    Espacialidade,
    PorteEvento,
)
from rh.models import Setor, UnidadeOrganizacional
from comum.models import Vinculo
from djtools.forms.fields.captcha import ReCaptchaField
import xlrd


class EventoForm(forms.ModelFormPlus):
    SUBMIT_LABEL = 'Submeter'
    dimensoes = forms.MultipleModelChoiceFieldPlus(label='Dimensões', queryset=Dimensao.objects.all(), required=True, widget=forms.CheckboxSelectMultiple())
    setor = forms.ModelChoiceFieldPlus(queryset=Setor.objects.all(), required=False, label='Setor')  # , widget=TreeWidget()
    classificacao = forms.ModelChoiceField(queryset=ClassificacaoEvento.objects.all(), label='Localização', widget=forms.RadioSelect(), empty_label=None, help_text='A classificação de um evento quanto à localização depende do envolvimento (parceria e articulação), participação (inscrição no evento) e localização do público-alvo (local de residência) para assim ser dimensionado.')
    porte = forms.ModelChoiceField(queryset=PorteEvento.objects.all(), label='Porte', widget=forms.RenderableRadioSelect('widgets/porteevento_widget.html'), empty_label=None)
    espacialidade = forms.ModelChoiceField(queryset=Espacialidade.objects.all(), label='Espacialidade', widget=forms.RadioSelect(), empty_label=None)
    tipo = forms.ModelChoiceField(queryset=TipoEvento.objects.all(), label='Tipo', required=True, widget=forms.RadioSelect())
    subtipo = forms.ModelChoiceField(label='Subtipo', queryset=SubtipoEvento.objects.all(), required=True, widget=forms.RenderableRadioSelect('widgets/subtipoevento_widget.html'))
    publico_alvo = forms.MultipleModelChoiceFieldPlus(label='Público Alvo', queryset=PublicoAlvoEvento.objects.all(), required=True, widget=forms.CheckboxSelectMultiple())
    hora_inicio = forms.TimeFieldPlus(label='Hora de Início', required=True)
    hora_fim = forms.TimeFieldPlus(label='Hora de Fim', required=True)
    hora_inicio_inscricoes = forms.TimeFieldPlus(label='Hora de Início das Inscrições', required=False)
    hora_fim_inscricoes = forms.TimeFieldPlus(label='Hora de Fim das Inscrições', required=False)
    campus = forms.ModelChoiceFieldPlus(label='Campus', queryset=UnidadeOrganizacional.objects.uo())
    organizadores = forms.MultipleModelChoiceFieldPlus(Vinculo.objects.pessoas_fisicas(), label='Organizadores')
    carga_horaria = forms.RegexField(label='Carga Horária', regex=r'^\d{1,}:([0-5]{1}[0-9]{1})$', required=False, help_text='Formato: "99:59"')

    class Meta:
        model = Evento
        exclude = ('deferido', 'motivo_indeferimento', 'ativo')

    class Media:
        js = ['/static/eventos/js/EventoForm.js']

    def __init__(self, *args, **kwargs):
        tipos_eventos = TipoEvento.objects.filter(subtipoevento__isnull=False).distinct()
        if kwargs.get('instance') and kwargs.get('instance').pk:
            instance = kwargs.get('instance')
            initial = kwargs.setdefault('initial', {})
            initial['carga_horaria'] = instance.carga_horaria_str
            if instance.get_carga_horaria():
                initial['carga_horaria'] = instance.get_carga_horaria()
        super().__init__(*args, **kwargs)
        self.is_avaliador_sistemico = Dimensao.is_avaliador_sistemico(self.request.user)
        self.is_avaliador_local = Dimensao.is_avaliador_local(self.request.user)
        if not self.is_avaliador_sistemico and not self.is_avaliador_local:
            servidor = self.request.user.get_relacionamento()
            self.fields['coordenador'].initial = servidor.pk
            self.fields['coordenador'].widget = forms.HiddenInput()
            self.fields['campus'].initial = servidor.setor.uo.pk
            self.fields['campus'].widget = forms.HiddenInput()
            self.fields['setor'].initial = servidor.setor
            self.fields['setor'].widget = forms.HiddenInput()
        else:
            self.fields['coordenador'].required = True

        if self.instance.pk:
            tipo_participacao = TipoParticipacao.objects.get(descricao='Organizador')
            self.fields['organizadores'].initial = list(
                self.instance.participantes.filter(tipo__tipo_participacao=tipo_participacao).values_list('vinculo_id', flat=True).distinct()
            )
        self.fields['tipo'].queryset = tipos_eventos

    def save(self, commit=True):
        pk = self.instance.pk
        super().save(commit=True)
        if not pk:
            HistoricoEvento.objects.create(evento=self.instance, descricao='Cadastrou o evento', user=self.request.user)

        return self.instance

    def save_m2m(self, *args, **kwargs):
        pass

    def clean_carga_horaria(self):
        carga_horaria = self.cleaned_data.get('carga_horaria')
        carga_horaria = Participante.tempo_para_segundos(carga_horaria)
        subtipo = self.data.get('subtipo')
        if subtipo and not SubtipoEvento.objects.get(pk=subtipo).multiplas_atividades and not carga_horaria:
            raise forms.ValidationError('A carga horária é obrigatória para eventos com uma única atividade.')
        return carga_horaria


class IndeferirEventoForm(forms.ModelFormPlus):
    motivo_indeferimento = forms.CharField(widget=forms.Textarea(), label='Motivo do Indeferimento')

    class Meta:
        model = Evento
        fields = ['motivo_indeferimento']

    def save(self, *args, **kwargs):
        instance = super().save(commit=False)
        self.instance.indeferir(self.instance.motivo_indeferimento, self.request.user)
        return instance


class JustificativaForm(forms.FormPlus):
    justificativa = forms.CharField(widget=forms.Textarea(), label='Justificativa')


class RelatorioEventosForm(forms.FormPlus):
    campus = forms.ModelChoiceField(label='Filtrar por Campus:', required=False, queryset=UnidadeOrganizacional.objects.suap(), empty_label='Todos')
    dimensao = forms.ModelChoiceField(label='Filtrar por Dimensão:', required=False, queryset=Dimensao.objects, empty_label='Todas')
    ano = forms.ChoiceField(label='Filtrar por Ano:', required=False, choices=[])
    setor = forms.ChoiceField(label='Filtrar por Setor:', required=False, choices=[])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        ANO_CHOICES = [['Todos', 'Todos']]
        _anos = (
            Evento.objects.extra({'year': "CAST(EXTRACT(YEAR FROM data_inicio) AS TEXT)"})
            .values_list('year')
            .annotate(total_item=Count('data_inicio'))
            .values_list('year', flat=True)
            .order_by('-year')
        )
        for a in _anos:
            ANO_CHOICES.append([str(a), str(a)])
        self.fields['ano'].choices = ANO_CHOICES

        SETOR_CHOICES = [['Todos', 'Todos']]
        setores = Evento.objects.filter(deferido=True, setor__isnull=False).values_list('setor', flat=True).order_by('setor')
        for setor in setores:
            nome_setor = Setor.objects.get(pk=setor)
            SETOR_CHOICES.append([str(setor), str(nome_setor.sigla)])
        self.fields['setor'].choices = SETOR_CHOICES


class RealizarInscricaoForm(forms.FormPlus):
    nome = forms.CharField(label='Nome')
    email = forms.EmailField(label='E-mail')
    cpf = forms.BrCpfField(label='CPF')
    telefone = forms.BrTelefoneField(label='Telefone', required=False)
    publico_alvo = forms.ModelChoiceFieldPlus2(PublicoAlvoEvento.objects.all(), label='Perfil')
    atividades = forms.MultipleModelChoiceField(AtividadeEvento.objects, label='Atividades', widget=forms.RenderableSelectMultiple('widgets/atividades_disponiveis_widget.html'))
    recaptcha = ReCaptchaField(label='Verificação')

    fieldsets = (
        ('Dados Gerais', {'fields': ('nome', ('email', 'telefone'), ('cpf', 'publico_alvo'), 'atividades', 'recaptcha')}),
    )

    def __init__(self, *args, **kwargs):
        self.evento = kwargs.pop('evento')
        super().__init__(*args, **kwargs)
        if self.evento.atividadeevento_set.exists():
            self.fields['atividades'].queryset = self.evento.atividadeevento_set.all()
        else:
            del(self.fields['atividades'])

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        if Participante.objects.filter(cpf=cpf, tipo__tipo_participacao__descricao='Participante', evento=self.evento).exists():
            raise forms.ValidationError('CPF já cadastrado para este evento.')
        return cpf

    def clean_publico_alvo(self):
        participante = Participante(cpf=self.cleaned_data.get('cpf'), publico_alvo=self.cleaned_data.get('publico_alvo'))
        participante.checar_vinculo()
        return self.cleaned_data.get('publico_alvo')

    def clean_atividades(self):
        atividades = self.cleaned_data.get('atividades')
        for atividade in atividades:
            qtd_disponiveis = atividade.get_qtd_vagas_disponiveis()
            if qtd_disponiveis is not None and qtd_disponiveis < 1:
                raise forms.ValidationError(f'Todas as vagas já foram preenchidas para atividade: {atividade}.')
        return atividades

    def _get_tipo_participacao(self):
        return TipoParticipacao.objects.get(descricao='Participante')

    def _get_tipo_participante(self):
        tipo_participacao = self._get_tipo_participacao()
        return TipoParticipante.objects.filter(evento=self.evento, tipo_participacao=tipo_participacao).first()

    def clean(self):
        cleaned_data = super().clean()
        tipo_participante = self._get_tipo_participante()
        qtd_disponiveis = tipo_participante.get_qtd_vagas_disponiveis()
        if qtd_disponiveis is not None and qtd_disponiveis < 1:
            raise forms.ValidationError('Todas as vagas já foram preenchidas.')

        return cleaned_data

    def processar(self):
        nome = self.cleaned_data.get('nome')
        email = self.cleaned_data.get('email')
        cpf = self.cleaned_data.get('cpf')
        telefone = self.cleaned_data.get('telefone')
        publico_alvo = self.cleaned_data.get('publico_alvo')
        tipo_participacao = self._get_tipo_participacao()
        tipo_participante = self._get_tipo_participante()
        if tipo_participante is None:
            tipo_participante = TipoParticipante.objects.create(evento=self.evento, tipo_participacao=tipo_participacao)
        qs = Participante.objects.filter(evento=self.evento, cpf=cpf, tipo=tipo_participante)
        if qs.exists():
            participante = qs.first()
        else:
            participante = Participante()
        participante.evento = self.evento
        participante.nome = nome
        participante.email = email
        participante.cpf = cpf
        participante.telefone = telefone
        participante.tipo = tipo_participante
        participante.inscricao_validada = False
        participante.publico_alvo = publico_alvo
        participante.checar_vinculo()
        participante.save()
        if 'atividades' in self.cleaned_data:
            for atividade in self.cleaned_data.get('atividades'):
                participante.atividades.add(atividade)


class InformarAtividadesForm(forms.ModelFormPlus):
    atividades = forms.MultipleModelChoiceField(AtividadeEvento.objects, label='Atividades', widget=forms.RenderableSelectMultiple('widgets/atividades_widget.html'), required=False)

    class Meta:
        model = Participante
        fields = ('atividades',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['atividades'].queryset = self.instance.evento.atividadeevento_set.all()


class InformarParticipantesForm(forms.FormPlus):
    cpfs = forms.CharField(
        label='CPFs',
        help_text='Informar CPF dos participantes seperados por espaço ou em linhas diferentes.',
        required=True, widget=forms.Textarea()
    )

    def processar(self, atividade_pk):
        atividade = AtividadeEvento.objects.get(pk=atividade_pk)
        cpfs = self.cleaned_data['cpfs'].replace('\n', ' ').split()
        for participante in atividade.evento.participantes.filter(cpf__in=cpfs):
            participante.atividades.add(atividade)


class AdicionarParticipanteEventoForm(forms.ModelFormPlus):
    atividades = forms.MultipleModelChoiceField(AtividadeEvento.objects, label='', widget=forms.RenderableSelectMultiple('widgets/atividades_widget.html'), required=False)

    class Meta:
        model = Participante
        fields = 'nome', 'cpf', 'email', 'telefone', 'publico_alvo', 'ch_extensao'

    fieldsets = (
        ('Dados Gerais', {'fields': (('nome', 'cpf'), ('email', 'telefone'), 'publico_alvo')}),
        ('Atividades do Evento', {'fields': ('atividades',)}),
    )

    def __init__(self, *args, **kwargs):
        self.evento = kwargs.pop('evento')
        self.tipo_participante = kwargs.pop('tipo_participante')
        super().__init__(*args, **kwargs)
        self.fields['atividades'].queryset = AtividadeEvento.objects.filter(evento=self.evento)
        self.fields['publico_alvo'].queryset = self.evento.publico_alvo.all()
        if not self.fields['atividades'].queryset.exists():
            self.fieldsets = (self.fieldsets[0],)

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        if Participante.objects.filter(cpf=cpf, tipo=self.tipo_participante, evento=self.instance.evento).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('CPF já cadastrado para este evento.')
        return cpf

    def clean_ch_extensao(self):
        ch_extensao = self.cleaned_data.get('ch_extensao')
        self.instance.cpf = self.data.get('cpf')
        if ch_extensao and not self.instance.is_aluno_extensao():
            raise forms.ValidationError('Não existe uma matrícula ativa para esse participante em curso que requer atividade curricular de extensão.')
        return ch_extensao

    def clean_publico_alvo(self):
        self.instance.cpf = self.cleaned_data.get('cpf')
        self.instance.publico_alvo = self.cleaned_data.get('publico_alvo')
        self.instance.checar_vinculo()
        return self.instance.publico_alvo

    def save(self, *args, **kwargs):
        participante = super().save(*args, **kwargs)
        for atividade in self.cleaned_data['atividades']:
            participante.atividades.add(atividade)


class EditarParticipanteEventoForm(forms.ModelFormPlus):

    class Meta:
        model = Participante
        fields = ('nome', 'cpf', 'email', 'telefone', 'publico_alvo', 'inscricao_validada', 'presenca_confirmada', 'ch_extensao')

    fieldsets = (
        ('Dados Gerais', {'fields': (('nome', 'cpf'), ('email', 'telefone'), 'publico_alvo')}),
        ('Dados da Participação', {'fields': (('inscricao_validada', 'presenca_confirmada',))}),
    )

    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', {})
        initial['atividades'] = kwargs['instance'].atividades.values_list('pk', flat=True)
        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)
        self.fields['publico_alvo'].queryset = self.instance.evento.publico_alvo.all()

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        if Participante.objects.filter(cpf=cpf, tipo=self.instance.tipo, evento=self.instance.evento).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('CPF já cadastrado para este evento.')
        return cpf

    def clean_ch_extensao(self):
        ch_extensao = self.cleaned_data.get('ch_extensao')
        if ch_extensao and not self.instance.is_aluno_extensao():
            raise forms.ValidationError('Não existe uma matrícula ativa para esse participante em curso que requer atividade curricular de extensão.')
        return ch_extensao

    def clean_publico_alvo(self):
        self.instance.cpf = self.cleaned_data.get('cpf')
        self.instance.publico_alvo = self.cleaned_data.get('publico_alvo')
        self.instance.checar_vinculo()
        return self.instance.publico_alvo


class ImportarParticipantesForm(forms.FormPlus):
    planilha = forms.FileFieldPlus(
        help_text='O arquivo deve ser no formato "xlsx", sem cabeçalho, contendo as seguintes colunas: CPF, Nome, E-mail e Perfil.',
        filetypes=['xlsx']
    )

    def __init__(self, evento, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.evento = evento
        self.participantes = []

    def clean(self):
        arquivo = self.cleaned_data.get('planilha')
        if arquivo:
            # Valida se eh XLS
            # -------------------------
            try:
                planilha = arquivo.file
                workbook = xlrd.open_workbook(file_contents=planilha.read())
            except Exception:
                raise forms.ValidationError(
                    'Não foi possível processar a planilha. '
                    'Verfique se o formato do arquivo é .xlsx,'
                )
            sheet = workbook.sheet_by_index(0)

            # Valida se existem 4 colunas
            # -------------------------
            if sheet.ncols < 4:
                raise forms.ValidationError('A planilha não contém as 4 colunas solicitadas.')

            erro = list()

            for i in range(0, sheet.nrows):
                publico_alvo = None
                dados = sheet.row_values(i)
                la = i + 1

                # Valida se cada uma das colunas tem os dados esperados
                # Dados solicitados na planilha
                # - CPF, Nome, E-mail e Perfil.

                # Valida Nome
                # ----------------
                nome = dados[1]
                if not nome:
                    erro.append(f'Nome inválido na linha {la}')

                # Valida Cpf
                # ----------------
                try:
                    cpf = int(dados[0])
                except ValueError:
                    cpf = dados[0]
                finally:
                    cpf = str(cpf)
                try:
                    cpf_field = BrCpfField()
                    cpf = cpf_field.clean(cpf)
                except forms.ValidationError:
                    erro.append(f'CPF inválido "{cpf}" na linha {la}')

                if Participante.objects.filter(cpf=cpf, evento=self.evento).exists():
                    erro.append(f'CPF repetido "{cpf}" na linha {la}')

                # Valida Email
                # ----------------
                email = dados[2]
                try:
                    email_field = forms.EmailField()
                    email = email_field.clean(email)
                except forms.ValidationError:
                    erro.append(f'Email inválido "{email}" na linha {la}')

                # Valida Perfil
                # ----------------
                descricao_publico_alvo = dados[3]
                if descricao_publico_alvo:
                    publico_alvo = self.evento.publico_alvo.filter(descricao__unaccent__iexact=descricao_publico_alvo).first()
                    if not publico_alvo:
                        erro.append(f'Perfil inválido "{descricao_publico_alvo}" na linha {la}')
                else:
                    erro.append(f'Perfil inválido "{descricao_publico_alvo}" na linha {la}')

                participante = self.evento.participantes.filter(cpf=cpf).first()
                if participante:
                    dados_atualizados = participante.nome != nome or participante.email != email
                else:
                    dados_atualizados = False
                    participante = Participante()
                participante.evento = self.evento
                participante.cpf = cpf
                participante.nome = nome
                participante.email = email
                participante.inscricao_validada = True
                if dados_atualizados and participante.certificado_enviado:
                    participante.certificado_enviado = False
                participante.publico_alvo = publico_alvo
                participante.checar_vinculo()
                self.participantes.append(participante)

            if erro:
                raise forms.ValidationError('A planilha contém o(s) '
                                            'seguinte(s) erro(s): </br>{}'.
                                            format('</br> '.join(erro)))

        return self.cleaned_data

    @transaction.atomic
    def processar(self, tipo_id):
        for participante in self.participantes:
            participante.tipo_id = tipo_id
            participante.save()


class BannerForm(forms.ModelFormPlus):
    class Meta:
        model = Banner
        fields = ('titulo', 'imagem', 'tipo', 'data_inicio', 'data_termino', 'link')

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('data_inicio') and cleaned_data.get('data_termino'):
            banners = Banner.objects.filter(data_inicio__lte=cleaned_data.get('data_termino'), data_termino__gte=cleaned_data.get('data_inicio'))
            if self.instance.pk:
                banners = banners.exclude(id=self.instance.id)
            if banners.exists():
                self.add_error('data_inicio', 'Já existe um banner ativo no período escolhido.')
        return cleaned_data


class AtendimentoPublicoForm(forms.ModelFormPlus):
    class Meta:
        model = AtendimentoPublico
        exclude = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.request.user
        if not user.has_perm('ae.add_tipoatendimento'):
            self.fields['campus'].queryset = self.fields['campus'].queryset.filter(id=get_uo(user).id)


class FotoEventoForm(forms.ModelFormPlus):
    class Meta:
        model = FotoEvento
        fields = ('imagem', 'descricao')

    fieldsets = (
        ('Dados Gerais', {'fields': ('imagem', 'descricao')}),
    )

    def save(self, evento):
        self.instance.evento = evento
        super().save()


class AnexoEventoForm(forms.ModelFormPlus):
    class Meta:
        model = AnexoEvento
        fields = ('arquivo', 'descricao')

    fieldsets = (
        ('Dados Gerais', {'fields': ('arquivo', 'descricao')}),
    )

    def save(self, evento):
        self.instance.evento = evento
        super().save()


class ImportarListaPresencaForm(forms.FormPlus):
    planilha = forms.FileFieldPlus(help_text='O arquivo deve ser no formato "xlsx", sem cabeçalho, contendo o CPF dos participantes.')

    def __init__(self, evento, tipo_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.evento = evento
        self.tipo_id = tipo_id
        self.participantes = []

    def clean(self):
        arquivo = self.cleaned_data.get('planilha')
        if arquivo:
            try:
                planilha = arquivo.file
                workbook = xlrd.open_workbook(file_contents=planilha.read())
            except Exception:
                raise forms.ValidationError(
                    'Não foi possível processar a planilha. Verfique se o formato do arquivo é .xlsx, sem cabeçalho e se contém o CPF.'
                )
            sheet = workbook.sheet_by_index(0)
            cpfs_invalidos = []
            for idx in range(0, sheet.nrows):
                try:
                    cpf = int(sheet.cell_value(idx, 0))
                except ValueError:
                    cpf = sheet.cell_value(idx, 0)
                finally:
                    cpf = str(cpf)
                try:
                    cpf_field = BrCpfField()
                    cpf = cpf_field.clean(cpf)
                except forms.ValidationError:
                    cpfs_invalidos.append(cpf)
                    continue

                participante = self.evento.participantes.filter(tipo_id=self.tipo_id, cpf=cpf).first()
                self.participantes.append(participante)

            if cpfs_invalidos:
                raise forms.ValidationError(
                    'A planilha contém os participantes com CPF inválido: {}. Faça a correção antes de importar a planilha.'.format(', '.join(cpfs_invalidos))
                )

        return self.cleaned_data

    @transaction.atomic
    def processar(self):
        for participante in self.participantes:
            if participante:
                participante.presenca_confirmada = True
                participante.save()


class EnviarMensagemForm(forms.Form):
    assunto = forms.CharField(label='Assunto')
    mensagem = forms.CharField(label='Mensagem', widget=forms.Textarea())

    def __init__(self, evento, *args, **kwargs):
        self.evento = evento
        super().__init__(*args, **kwargs)

    def processar(self):
        pass


class AtividadeEventoForm(forms.ModelFormPlus):
    data = forms.DateFieldPlus(label='Data', required=False)
    hora = forms.TimeFieldPlus(label='Hora', required=False)
    ch = forms.RegexField(label='Carga Horária', regex=r'^\d{1,}:([0-5]{1}[0-9]{1})$', required=True, help_text='Formato: "99:59"')

    def __init__(self, *args, **kwargs):
        if kwargs.get('instance') and kwargs.get('instance').pk:
            initial = kwargs.setdefault('initial', {})
            initial['ch'] = kwargs.get('instance').get_ch()
        super().__init__(*args, **kwargs)

    class Meta:
        model = AtividadeEvento
        exclude = ('participantes', )

    def clean_ch(self):
        tempo_ch = self.cleaned_data.get('ch')
        return Participante.tempo_para_segundos(tempo_ch)
