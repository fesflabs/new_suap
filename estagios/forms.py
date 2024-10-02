import datetime
from collections import OrderedDict

from dateutil.relativedelta import relativedelta

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.db import transaction
from django.db.models.fields.files import FieldFile
from django.forms.models import BaseInlineFormSet

from comum.utils import get_uo
from djtools import forms
from djtools.forms.fields.captcha import ReCaptchaField
from djtools.forms import BrCnpjWidget
from djtools.forms.widgets import AutocompleteWidget, Select
from djtools.templatetags.filters import in_group, format_
from djtools.utils import send_notification
from edu.models import Professor, Aluno, Turno, CursoCampus, Modalidade, Estado, Cidade
from estagios.models import (
    OfertaPraticaProfissional,
    Convenio,
    PraticaProfissional,
    VisitaPraticaProfissional,
    Atividade,
    EstagioAditivoContratual,
    RelatorioSemestralEstagio,
    TipoRemuneracao,
    OrientacaoEstagio,
    TipoAditivo,
    RelatorioSemestralEstagioAtividade,
    Aprendizagem,
    ModuloAprendizagem,
    AditivoContratualAprendizagem,
    TipoAditivoAprendizagem,
    VisitaAprendizagem,
    OrientacaoAprendizagem,
    RelatorioModuloAprendizagem,
    SolicitacaoCancelamentoEncerramentoEstagio,
    AtividadeProfissionalEfetiva,
    OrientacaoAtividadeProfissionalEfetiva,
    JustificativaVisitaEstagio,
    JustificativaVisitaModuloAprendizagem,
)
from estagios.utils import ListCharField
from rh.models import Pessoa, PessoaJuridica, UnidadeOrganizacional, PessoaFisica
from comum.models import Vinculo


class AtLeastOneFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        non_empty_forms = 0
        for form in self:
            if form.cleaned_data:
                non_empty_forms += 1
        if non_empty_forms - len(self.deleted_forms) < 1:
            raise forms.ValidationError("Ao menos uma atividade deve ser adicionada ao plano.")


class PraticaProfissionalForm(forms.ModelFormPlus):
    estado = forms.ModelChoiceField(queryset=Estado.objects, label='Unidade da Federação', required=False, widget=Select())
    cidade = forms.ModelChoiceFieldPlus(
        Cidade.objects, label='Município', required=False, widget=AutocompleteWidget(search_fields=Cidade.SEARCH_FIELDS, form_filters=[('estado', 'estado__in')])
    )
    orientador = forms.ModelChoiceFieldPlus(
        Professor.objects, label='Professor Orientador', required=True, widget=AutocompleteWidget(search_fields=Professor.SEARCH_FIELDS)
    )
    email_supervisor = forms.EmailField(label='E-mail', help_text='Este e-mail será importante para o envio da avaliação.')
    supervisor = forms.ModelChoiceFieldPlus(
        PessoaFisica.objects,
        label='Supervisor',
        help_text="Só preencher esse campo, se for utilizar a funcionalidade de Documento Eletrônico.",
        required=False,
        widget=AutocompleteWidget(search_fields=PessoaFisica.SEARCH_FIELDS),
    )

    fieldsets = (
        ('Dados Gerais',
            {
                'fields': (
                    'obrigatorio',
                    'turno', 'aluno',
                    ('convenio', 'orientador'),
                    ('servidor_representante', 'agente_integracao')
                )
            }
         ),
        ('Concedente e o Endereço de seu Estabelecimento',
            {
                'fields': (
                    'empresa',
                    'representante_concedente',
                    ('nome_representante_concedente', 'cargo_representante_concedente'),
                    'ramo_atividade',
                    ('estado', 'cidade'),
                    ('logradouro', 'numero'),
                    'complemento',
                    ('bairro', 'cep'),
                )
            },
         ),
        ('Bolsa',
            {
                'fields': (
                    ('remunerada', 'tipo_remuneracao'),
                    'valor',
                    ('auxilio_transporte', 'auxilio_alimentacao'),
                    'descricao_outros_beneficios'
                )
            }
         ),
        ('Período e Carga Horária',
            {
                'fields': (
                    ('data_inicio', 'data_prevista_fim'),
                    ('ch_semanal', 'ch_diaria', 'horario')
                )
            }
         ),
        ('Documentação',
            {
                'fields': (
                    'relatorio_avaliacao_instalacoes',
                    ('plano_atividades', 'termo_compromisso'),
                    ('testemunha1', 'testemunha_1'),
                    ('testemunha2', 'testemunha_2')
                )
            }
         ),
        ('Seguro',
            {
                'fields': (
                    ('nome_da_seguradora', 'cnpj_da_seguradora'),
                    'numero_seguro'
                )
            }
         ),
        ('Supervisor',
            {
                'fields': (
                    'supervisor',
                    'nome_supervisor',
                    'cargo_supervisor',
                    ('telefone_supervisor', 'email_supervisor'),
                    'observacao'
                )
            }
         ),
    )

    class Meta:
        model = PraticaProfissional
        fields = (
            'tipo',
            'obrigatorio',
            'turno',
            'aluno',
            'convenio',
            'empresa',
            'orientador',
            'remunerada',
            'tipo_remuneracao',
            'valor',
            'data_inicio',
            'data_prevista_fim',
            'ch_semanal',
            'relatorio_avaliacao_instalacoes',
            'plano_atividades',
            'termo_compromisso',
            'numero_seguro',
            'nome_supervisor',
            'telefone_supervisor',
            'cargo_supervisor',
            'email_supervisor',
            'observacao',
            'auxilio_transporte',
            'auxilio_alimentacao',
            'descricao_outros_beneficios',
            'estado',
            'cidade',
            'logradouro',
            'numero',
            'complemento',
            'bairro',
            'cep',
            'nome_representante_concedente',
            'cargo_representante_concedente',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.fields['orientador'].queryset = Professor.servidores_docentes.all()
        self.fields['obrigatorio'].required = True
        self.fields['aluno'].widget = AutocompleteWidget(search_fields=Aluno.SEARCH_FIELDS)
        if in_group(self.request.user, ['Coordenador de Estágio']) and not in_group(self.request.user, ['Coordenador de Estágio Sistêmico', 'estagios Administrador']):
            self.fields['aluno'].queryset = self.fields['aluno'].queryset.filter(matriz__isnull=False, curso_campus__diretoria__setor__uo=get_uo(self.request.user)).order_by('-pk')
        else:
            self.fields['aluno'].queryset = self.fields['aluno'].queryset.filter(matriz__isnull=False).order_by('-pk')

        self.fields['empresa'].widget = AutocompleteWidget(search_fields=Pessoa.SEARCH_FIELDS)
        self.fields['empresa'].queryset = self.fields['empresa'].queryset.all()
        self.fields['cnpj_da_seguradora'].widget = BrCnpjWidget()
        if self.instance.cidade:
            self.fields['estado'].initial = self.instance.cidade.estado.pk

    def clean(self):
        cleaned_data = super().clean()
        #
        estagio_eh_obrigatorio = cleaned_data.get('obrigatorio')
        estagio_eh_remunerado = cleaned_data.get('remunerada')
        estagio_tem_valor = cleaned_data.get('valor') or 0 > 0
        if not estagio_eh_obrigatorio and not estagio_eh_remunerado:
            self._errors['remunerada'] = self.error_class(['Estágio não-obrigatório exige remuneração.'])
            del self.cleaned_data['remunerada']
        elif estagio_eh_remunerado and not estagio_tem_valor:
            self._errors['valor'] = self.error_class(['Estágio remunerado exige o valor da bolsa.'])
            if 'valor' in self.cleaned_data:
                del self.cleaned_data['valor']
        elif not estagio_eh_remunerado and estagio_tem_valor:
            self._errors['remunerada'] = self.error_class(['Para ter bolsa, o estágio deve ser remunerado.'])
            del self.cleaned_data['remunerada']
        #
        return cleaned_data

    def save(self, *args, **kwargs):
        pk = self.instance.pk
        email_supervisor = None
        if pk:
            pratica = PraticaProfissional.objects.filter(pk=pk).first()
            if pratica:
                email_supervisor = pratica.email_supervisor
        retorno = super().save(*args, **kwargs)
        if pk:
            if email_supervisor != self.cleaned_data.get('email_supervisor'):
                self.instance.enviar_email_supervisor_recem_cadastrado(self.request.user)
        else:
            self.instance.enviar_emails_estagio_recem_cadastrado(self.request.user)

        return retorno


class EstagioAditivoContratualForm(forms.ModelFormPlus):
    TIPO_CHOICES = [
        [1, 'Professor Orientador'],
        [2, 'Remuneração'],
        [3, 'Transporte'],
        [4, 'Alimentação'],
        [5, 'Tempo'],
        [6, 'Carga Horária'],
        [7, 'Plano de Atividade'],
        [8, 'Supervisor'],
        [9, 'Horário'],
    ]
    # tipos_aditivo = forms.ModelMultipleChoiceField(TipoAditivo.objects.all(), label=u'Tipo', widget=forms.CheckboxSelectMultiple(), )

    # 1
    orientador = forms.ModelChoiceFieldPlus(Professor.objects, label='Orientador', required=False)
    # 2
    remunerada = forms.BooleanField(label='Remunerada', required=False)
    tipo_remuneracao = forms.ModelChoiceField(TipoRemuneracao.objects.all(), label='Tipo de Remuneração', required=False)
    valor = forms.DecimalFieldPlus(label='Bolsa (R$)', required=False)
    # 3
    auxilio_transporte = forms.DecimalFieldPlus(label='Auxílio Transporte (R$)', required=False)
    # 4
    auxilio_alimentacao = forms.DecimalFieldPlus(label='Outros Benefícios (R$)', required=False)
    descricao_outros_beneficios = forms.CharFieldPlus(label='Descrição', required=False, help_text='Descrição de outros benefícios recebidos.', widget=forms.Textarea())
    # 5
    data_prevista_fim = forms.DateFieldPlus(label='Data Prevista para Encerramento', required=False)
    # 6
    ch_semanal = forms.IntegerField(label='C.H. Semanal', required=False)
    # 7
    plano_atividades = forms.FileFieldPlus(label='Plano de Atividades', required=False, help_text='Adicionar arquivo no caso o plano de atividades vir separado.')
    lista_atividades = ListCharField(label='Atividades', required=False)
    # 8
    nome_supervisor = forms.CharFieldPlus(label='Nome', required=False)
    telefone_supervisor = forms.CharFieldPlus(label='Telefone', required=False)
    cargo_supervisor = forms.CharFieldPlus(label='Cargo', required=False)
    email_supervisor = forms.EmailField(label='E-mail', required=False)
    observacao = forms.CharFieldPlus(label='Observação', required=False, widget=forms.Textarea())
    # 9
    turno = forms.ModelChoiceField(Turno.objects.all(), label='Turno', required=False)
    # 10
    nome_da_seguradora = forms.CharFieldPlus(label='Nome da Seguradora', required=False)
    numero_seguro = forms.CharFieldPlus(label='Número da Apólice do Seguro', required=False)

    class Meta:
        model = EstagioAditivoContratual
        fields = ('tipos_aditivo', 'descricao', 'aditivo', 'inicio_vigencia')

    class Media:
        js = ('/static/estagios/js/EstagioAditivoContratualForm.js',)

    fieldsets = (
        ('Dados Gerais', {'fields': ('tipos_aditivo', ('inicio_vigencia', 'aditivo'), 'descricao')}),
        ('Aditivo de Professor Orientador', {'fields': ('orientador',)}),
        ('Aditivo de Remuneração', {'fields': ('remunerada', ('tipo_remuneracao', 'valor'))}),
        ('Aditivo de Auxílio Transporte', {'fields': ('auxilio_transporte',)}),
        ('Aditivo de Outros Benefícios', {'fields': (('auxilio_alimentacao', 'descricao_outros_beneficios'),)}),
        ('Aditivo de Tempo', {'fields': ('data_prevista_fim',)}),
        ('Aditivo de Carga Horária Semanal', {'fields': ('ch_semanal',)}),
        ('Aditivo de Plano de Atividades', {'fields': ('plano_atividades', 'lista_atividades')}),
        ('Aditivo de Supervisor', {'fields': ('nome_supervisor', 'telefone_supervisor', 'cargo_supervisor', 'email_supervisor', 'observacao')}),
        ('Aditivo de Horário', {'fields': ('turno',)}),
        ('Aditivo de Seguro', {'fields': ('nome_da_seguradora', 'numero_seguro')}),
    )

    #     def clean(self):
    #         #tipos_aditivo = self.cleaned_data['tipos_aditivo']
    #         #fields = self.fieldsets[tipos_aditivo][1]['fields']
    #         for field in fields:
    #             if field != 'observacao':
    #                 if not self.cleaned_data.get(field):
    #                     raise forms.ValidationError(u'Preencha todos os campos do formulário')
    #         return self.cleaned_data

    def __init__(self, pratica_profissional, *args, **kwargs):
        TipoAditivo.objects.get_or_create(id=TipoAditivo.PROFESSOR_ORIENTADOR, descricao='Professor Orientador')
        TipoAditivo.objects.get_or_create(id=TipoAditivo.REMUNERACAO, descricao='Remuneração')
        TipoAditivo.objects.get_or_create(id=TipoAditivo.TRANSPORTE, descricao='Transporte')
        TipoAditivo.objects.get_or_create(id=TipoAditivo.OUTROS_BENEFICIOS, descricao='Outros Benefícios')
        TipoAditivo.objects.get_or_create(id=TipoAditivo.TEMPO, descricao='Tempo')
        TipoAditivo.objects.get_or_create(id=TipoAditivo.CARGA_HORARIA, descricao='Carga Horária')
        TipoAditivo.objects.get_or_create(id=TipoAditivo.PLANO_DE_ATIVIDADE, descricao='Plano de Atividade')
        TipoAditivo.objects.get_or_create(id=TipoAditivo.SUPERVISOR, descricao='Supervisor')
        TipoAditivo.objects.get_or_create(id=TipoAditivo.HORARIO, descricao='Horário')
        TipoAditivo.objects.get_or_create(id=TipoAditivo.SEGURO, descricao='Seguro')

        super().__init__(*args, **kwargs)
        # self.fields['orientador'].queryset = Professor.servidores_docentes.all()
        self.fields['tipos_aditivo'].widget = forms.CheckboxSelectMultiple()
        self.fields['tipos_aditivo'].queryset = TipoAditivo.objects.all()
        ####
        # inicializa a lista de atividades (copia da lista atual)
        lista_atividades_atual = []
        for atividade in pratica_profissional.atividade_set.all():
            lista_atividades_atual.append(f'{atividade.descricao}')
        self.fields['lista_atividades'].initial = lista_atividades_atual
        ####
        self.instance.pratica_profissional = pratica_profissional
        self.fields['inicio_vigencia'].label = 'Início da Vigência'

    def clean(self):
        cleaned_data = super().clean()

        def clean_dict(key):
            try:
                del self.cleaned_data[key]
            except Exception:
                pass
        #
        estagio_eh_obrigatorio = self.instance.pratica_profissional.obrigatorio
        estagio_eh_remunerado = cleaned_data.get('remunerada')
        estagio_tem_valor = cleaned_data.get('valor') or 0 > 0
        if 'tipos_aditivo' not in self.cleaned_data:
            self._errors['tipos_aditivo'] = self.error_class(['Selecione pelo menos um tipo de aditivo contratual.'])
        else:
            if TipoAditivo.objects.get(pk=TipoAditivo.REMUNERACAO) in self.cleaned_data['tipos_aditivo']:
                if not estagio_eh_obrigatorio and not estagio_eh_remunerado:
                    self._errors['remunerada'] = self.error_class(['Estágio não-obrigatório exige remuneração.'])
                    clean_dict('remunerada')
                elif estagio_eh_remunerado and not estagio_tem_valor:
                    self._errors['valor'] = self.error_class(['Estágio remunerado exige o valor da bolsa.'])
                    clean_dict('valor')
                elif not estagio_eh_remunerado and estagio_tem_valor:
                    self._errors['remunerada'] = self.error_class(['Para ter bolsa, o estágio deve ser remunerado.'])
                    clean_dict('remunerada')
            #
            if TipoAditivo.objects.get(pk=TipoAditivo.PROFESSOR_ORIENTADOR) in self.cleaned_data['tipos_aditivo']:
                if not cleaned_data.get('orientador'):
                    self._errors['orientador'] = self.error_class(['Deve ser informado o novo professor orientador.'])
                    clean_dict('orientador')
            if TipoAditivo.objects.get(pk=TipoAditivo.TRANSPORTE) in self.cleaned_data['tipos_aditivo']:
                if not cleaned_data.get('auxilio_transporte'):
                    self._errors['auxilio_transporte'] = self.error_class(['Deve ser informado o valor do auxílio transporte.'])
                    clean_dict('auxilio_transporte')
            if TipoAditivo.objects.get(pk=TipoAditivo.OUTROS_BENEFICIOS) in self.cleaned_data['tipos_aditivo']:
                if not cleaned_data.get('auxilio_alimentacao'):
                    self._errors['auxilio_alimentacao'] = self.error_class(['Deve ser informado o valor dos outros benefícios'])
                    clean_dict('auxilio_alimentacao')
                if not cleaned_data.get('descricao_outros_beneficios'):
                    self._errors['descricao_outros_beneficios'] = self.error_class(['Deve ser informada uma descrição para os outros benefícios'])
                    clean_dict('descricao_outros_beneficios')
            if TipoAditivo.objects.get(pk=TipoAditivo.TEMPO) in self.cleaned_data['tipos_aditivo']:
                if not cleaned_data.get('data_prevista_fim'):
                    self._errors['data_prevista_fim'] = self.error_class(['Deve ser informada a nova data prevista para encerramento.'])
                    clean_dict('data_prevista_fim')
            if TipoAditivo.objects.get(pk=TipoAditivo.CARGA_HORARIA) in self.cleaned_data['tipos_aditivo']:
                if not cleaned_data.get('ch_semanal'):
                    self._errors['ch_semanal'] = self.error_class(['Deve ser informada a nova carga horária deste estágio.'])
                    clean_dict('ch_semanal')
            if TipoAditivo.objects.get(pk=TipoAditivo.SUPERVISOR) in self.cleaned_data['tipos_aditivo']:
                if not cleaned_data.get('nome_supervisor'):
                    self._errors['nome_supervisor'] = self.error_class(['Deve ser informado o nome do novo supervisor deste estágio.'])
                    clean_dict('nome_supervisor')
                if not cleaned_data.get('telefone_supervisor'):
                    self._errors['telefone_supervisor'] = self.error_class(['Deve ser informado o telefone do novo supervisor deste estágio.'])
                    clean_dict('telefone_supervisor')
                if not cleaned_data.get('cargo_supervisor'):
                    self._errors['cargo_supervisor'] = self.error_class(['Deve ser informado o cargo do novo supervisor deste estágio.'])
                    clean_dict('cargo_supervisor')
                if not cleaned_data.get('email_supervisor'):
                    self._errors['email_supervisor'] = self.error_class(['Deve ser informado o e-mail do novo supervisor deste estágio.'])
                    clean_dict('email_supervisor')
            if TipoAditivo.objects.get(pk=TipoAditivo.HORARIO) in self.cleaned_data['tipos_aditivo']:
                if not cleaned_data.get('turno'):
                    self._errors['turno'] = self.error_class(['Deve ser informado o novo turno deste estágio.'])
                    clean_dict('turno')
            if TipoAditivo.objects.get(pk=TipoAditivo.SEGURO) in self.cleaned_data['tipos_aditivo']:
                if not cleaned_data.get('nome_da_seguradora'):
                    self._errors['nome_da_seguradora'] = self.error_class(['Deve ser informado o nome da seguradora.'])
                    clean_dict('nome_da_seguradora')
                if not cleaned_data.get('numero_seguro'):
                    self._errors['numero_seguro'] = self.error_class(['Deve ser informado o número do seguro.'])
                    clean_dict('numero_seguro')
        return cleaned_data

    @transaction.atomic
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        nova_lista_de_atividades_estagio = []
        historico = []
        for key, value in list(self.cleaned_data.items()):
            if key != 'tipos_aditivo':
                ha_value = value
                ha_aditivo_remuneracao = key == 'valor' and ha_value  # attr 'Remunerada' pode vir 'False', devendo ser registrado no histórico
                if (ha_value or ha_aditivo_remuneracao) and (key == 'lista_atividades' or hasattr(self.instance.pratica_profissional, key)):
                    if key == 'lista_atividades':
                        if TipoAditivo.objects.get(pk=TipoAditivo.PLANO_DE_ATIVIDADE) in self.cleaned_data['tipos_aditivo']:
                            anterior = [atividade.descricao for atividade in self.instance.pratica_profissional.atividade_set.all()]
                            nova_lista_de_atividades_estagio = value
                            rotulo = 'Relação de Atividades do Estágio'
                            historico.append(f'{rotulo}: {format_(anterior)} → {format_(value)}')
                    else:
                        anterior = getattr(self.instance.pratica_profissional, key, value)
                        if value and value.__class__ in [InMemoryUploadedFile, TemporaryUploadedFile]:
                            value = value.name
                        setattr(self.instance.pratica_profissional, key, value)
                        if isinstance(anterior, FieldFile):
                            anterior = anterior.name
                        if anterior in [True, False]:
                            anterior = anterior and 'Sim' or 'Não'
                        if value in [True, False]:
                            value = value and 'Sim' or 'Não'
                        rotulo = self.instance.pratica_profissional._meta.get_field(key).verbose_name
                        historico.append(f'{rotulo}: {format_(anterior)} → {format_(value)}')

        self.instance.pratica_profissional.save()
        ##
        if nova_lista_de_atividades_estagio:
            # mescla (pela descrição da atividade) as atividades anteriores com as novas atividades
            atividades_anteriores = [atividade.descricao for atividade in self.instance.pratica_profissional.atividade_set.all()]
            for nova_atividade in nova_lista_de_atividades_estagio:
                if nova_atividade and nova_atividade not in atividades_anteriores:
                    atividade = Atividade()
                    atividade.pratica_profissional = self.instance.pratica_profissional
                    atividade.descricao = f'{nova_atividade}'
                    atividade.save()
            for atividade_antiga in Atividade.objects.filter(pratica_profissional=self.instance.pratica_profissional):
                if atividade_antiga.descricao not in nova_lista_de_atividades_estagio:
                    atividade_antiga.delete()

        ##
        self.instance.historico = '\n'.join(historico)
        self.instance.save()
        if self.instance.tipos_aditivo.filter(pk=TipoAditivo.PROFESSOR_ORIENTADOR).exists():
            send_notification(
                '[SUAP] Nova Orientação de Estágio',
                '<h1>Nova Orientação de Estágio</h1><p>O estagiário {} passou a ter uma prática profissional sob sua orientação.</p>'.format(
                    self.instance.pratica_profissional.aluno
                ),
                settings.DEFAULT_FROM_EMAIL,
                [self.instance.pratica_profissional.orientador.vinculo],
            )

        if self.instance.tipos_aditivo.filter(pk=TipoAditivo.SUPERVISOR).exists():
            send_notification(
                '[SUAP] Novo Supervisor de Estágio',
                '<h1>Novo Supervisor de Estágio</h1><p>O estagiário {} passou a ter nova supervisão uma prática profissional sob sua orientação.</p>'.format(
                    self.instance.pratica_profissional.aluno
                ),
                settings.DEFAULT_FROM_EMAIL,
                [self.instance.pratica_profissional.orientador.vinculo],
            )
            send_notification(
                '[SUAP] Novo Supervisor de Estágio',
                '<h1>Novo Supervisor de Estágio</h1><p>Prezado estagiário, foi cadastrado nova supervisão em sua prática profissional.</p>',
                settings.DEFAULT_FROM_EMAIL,
                [self.instance.pratica_profissional.aluno.get_vinculo()],
            )


class EncerrarPraticaProfissionalForm(forms.ModelFormPlus):

    class Meta:
        model = PraticaProfissional
        fields = (
            'data_fim',
            'movito_encerramento',
            'motivacao_desligamento_encerramento',
            'motivo_rescisao',
            'ch_final',
            'termo_encerramento',
            'ficha_frequencia',
            'estagio_anterior_20161',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ch_final'].help_text = self.instance.get_sugestao_ch_final()

    fieldsets = (
        ('Dados do Encerramento', {'fields': ('movito_encerramento', 'motivacao_desligamento_encerramento', 'motivo_rescisao', 'data_fim', 'ch_final')}),
        ('Documentação', {'fields': ('termo_encerramento', 'ficha_frequencia')}),
        ('Finalizar sem visitas e demais dados', {'fields': ('estagio_anterior_20161',)}),
    )

    def clean(self):
        # Para encerrar a prática profissional é necessário o cadastro de visitas do orientador, relatorios de
        # atividades de estagiário, avaliacao do supervisor. Salvo caso o estágio a data prevista para encerramento
        # já seja passada e seja selecionada a opção estagio_anterior_20161.

        cleaned_data = super().clean()
        data_encerramento = cleaned_data.get('data_fim', None)

        if data_encerramento:
            movito_encerramento = cleaned_data.get('movito_encerramento', None)
            estagio_anterior_20161 = cleaned_data.get('estagio_anterior_20161', False)
            final_do_periodo = datetime.date(2017, 4, 30)

            if estagio_anterior_20161 and data_encerramento > final_do_periodo:
                self._errors['data_fim'] = self.error_class(['O estágio deve ter data do encerramento até 30/04/2017.'])
                self._errors['estagio_anterior_20161'] = self.error_class(['Verifique a data do encerramento.'])
                del self.cleaned_data['data_fim']
                del self.cleaned_data['estagio_anterior_20161']

            if movito_encerramento == PraticaProfissional.MOTIVO_CONCLUSAO:
                if data_encerramento != self.instance.data_prevista_fim:
                    raise forms.ValidationError('Data do Encerramento diferente da data prevista para o fim.')
                if not estagio_anterior_20161:
                    if self.instance.ha_pendencia_de_visita(data_encerramento):
                        raise forms.ValidationError('Não é possível encerrar o estágio, pois o professor orientador não cadastrou as visitas de cada trimestre.')
                    for visita in self.instance.visitapraticaprofissional_set.all():
                        if not visita.relatorio:
                            raise forms.ValidationError(
                                f'Não é possível encerrar o estágio, pois a visita realizada no dia {format_(visita.data_visita)} não contém o arquivo do relatório.'
                            )
                    if self.instance.ha_pendencia_relatorio_estagiario(data_encerramento):
                        raise forms.ValidationError('Não é possível encerrar o estágio, pois o estagiário não cadastrou todos os relatórios semestrais.')
                    if self.instance.ha_pendencia_relatorio_supervisor(data_encerramento):
                        raise forms.ValidationError('Não é possível encerrar o estágio, pois o supervisor não realizou todas as avaliações do estágio.')
            elif movito_encerramento == PraticaProfissional.MOTIVO_RESCISAO:
                primeiro_periodo_trimestral = self.instance.get_periodos_trimestrais()[0]
                encerramento_eh_maior_que_3_meses = data_encerramento > primeiro_periodo_trimestral['fim']
                if not estagio_anterior_20161:
                    if encerramento_eh_maior_que_3_meses:
                        if not self.instance.visitapraticaprofissional_set.exists() and self.instance.ha_pendencia_de_visita(data_encerramento):
                            raise forms.ValidationError('Não é possível encerrar o estágio, pois o professor orientador não cadastrou visita alguma.')
                        if self.instance.ha_pendencia_relatorio_estagiario(data_encerramento):
                            raise forms.ValidationError('Não é possível encerrar o estágio, pois o estagiário não cadastrou todos os relatórios semestrais.')
                        if self.instance.ha_pendencia_relatorio_supervisor(data_encerramento):
                            raise forms.ValidationError('Não é possível encerrar o estágio, pois o supervisor não realizou todas as avaliações do estágio.')
        return cleaned_data


class EncerrarEstagioAbandonoMatriculaIrregularForm(forms.ModelFormPlus):
    class Meta:
        model = PraticaProfissional
        fields = ('data_fim', 'movito_encerramento', 'motivacao_desligamento_encerramento', 'motivo_rescisao', 'ch_final', 'desvinculado_matricula_irregular')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ch_final'].help_text = self.instance.get_sugestao_ch_final()
        self.fields['desvinculado_matricula_irregular'].required = True
        self.fields['motivo_rescisao'].required = True

    fieldsets = (
        ('Dados do Encerramento', {'fields': ('movito_encerramento', 'motivacao_desligamento_encerramento', 'motivo_rescisao', 'data_fim', 'ch_final')}),
        ('Finalizar sem requisitos por abandono do aluno/matrícula irregular', {'fields': ('desvinculado_matricula_irregular',)}),
    )

    def clean(self):
        cleaned_data = super().clean()
        desvinculado_matricula_irregular = cleaned_data.get('desvinculado_matricula_irregular', None)
        if not desvinculado_matricula_irregular:
            self._errors['desvinculado_matricula_irregular'] = self.error_class(['Necessária confirmação.'])


class RelatorioSemestralEstagioForm(forms.ModelFormPlus):

    periodo = forms.ChoiceField(label='Período', required=True)

    class Meta:
        model = RelatorioSemestralEstagio
        exclude = ('pratica_profissional', 'eh_relatorio_do_supervisor', 'inicio', 'fim', 'ultimo_editor')

    fieldsets = (('Período e Data do Relatório', {'fields': ('periodo', 'data_relatorio')}),)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pratica_profissional = self.instance.pratica_profissional

        self.atividades = set()
        self.fieldsets += (('Atividades Previstas', {'fields': self.atividades}),)
        self.fieldsets += (
            ('Sobre o Plano de Atividades', {'fields': ('comentarios_atividades', 'realizou_outras_atividades', 'outras_atividades', 'outras_atividades_justificativa')}),
        )

        if not self.instance.eh_relatorio_do_supervisor:
            self.fieldsets += (('Relação Teoria/Prática', {'fields': ('estagio_na_area_formacao', 'estagio_contribuiu', 'aplicou_conhecimento')}),)
            self.fieldsets += (('Avaliação do Estágio', {'fields': ('avaliacao_conceito',)}),)
            self.fieldsets += (('Comentários e Sugestões', {'fields': ('avaliacao_comentarios',)}),)
            del self.fields['nota_estagiario']
        if self.instance.eh_relatorio_do_supervisor:
            self.fieldsets += (('Avaliação do Desempenho do Estagiário', {'fields': ('nota_estagiario',)}),)
        self.fieldsets += (('Relatório', {'fields': ('relatorio',)}),)
        #
        self.atividades.clear()
        for atividade in pratica_profissional.atividade_set.all():
            pk = str(atividade.pk)
            field_realizada = f'{pk}.realizada'
            field_motivo = f'{pk}.nao_realizada_motivo'
            field_motivo_descricao = f'{pk}.nao_realizada_motivo_descricao'
            if self.instance.pk and self.instance.relatoriosemestralestagioatividade_set.filter(atividade=atividade).exists():
                avaliacao_atividade = self.instance.relatoriosemestralestagioatividade_set.get(atividade=atividade)
            else:
                avaliacao_atividade = RelatorioSemestralEstagioAtividade()

            self.fields[field_realizada] = forms.ChoiceField(
                label=atividade.descricao, choices=[[0, '-------']] + RelatorioSemestralEstagioAtividade.REALIZADA_CHOICES, initial=avaliacao_atividade.realizada
            )
            self.fields[field_motivo] = forms.ChoiceField(
                label='Motivo',
                choices=[[None, '-------']] + RelatorioSemestralEstagioAtividade.NAO_REALIZADA_MOTIVO_CHOICES,
                required=False,
                initial=avaliacao_atividade.nao_realizada_motivo,
                help_text='Em caso de atividade não realizada.',
            )
            self.fields[field_motivo_descricao] = forms.CharFieldPlus(label='Descrição de Outro Motivo', initial=avaliacao_atividade.nao_realizada_motivo_descricao, required=False)
            #
            self.atividades.add((field_realizada, field_motivo, field_motivo_descricao))

        initial, choices = self.gerar_lista_periodos()
        self.fields['periodo'].initial = initial
        self.fields['periodo'].choices = choices

    def gerar_lista_periodos(self):
        pratica_profissional = self.instance.pratica_profissional
        lista_combo = [[0, '-------']]
        if self.instance.pk:
            lista_combo += ([1, f'[{format_(self.instance.inicio)} até {format_(self.instance.fim)}]'],)
            initial = 1
        else:
            count = 1
            for periodo in pratica_profissional.get_periodos_semestrais():
                if self.request.user.has_perm('estagios.add_praticaprofissional'):
                    if periodo['inicio'] < datetime.date.today():
                        if not pratica_profissional.relatoriosemestralestagio_set.filter(
                            eh_relatorio_do_supervisor=self.instance.eh_relatorio_do_supervisor, inicio=periodo['inicio'], fim=periodo['fim']
                        ).exists():
                            lista_combo += ([count, '[{} até {}]'.format(format_(periodo['inicio']), format_(periodo['fim']))],)
                else:
                    if periodo['fim'] < datetime.date.today():
                        if not pratica_profissional.relatoriosemestralestagio_set.filter(
                            eh_relatorio_do_supervisor=self.instance.eh_relatorio_do_supervisor, inicio=periodo['inicio'], fim=periodo['fim']
                        ).exists():
                            lista_combo += ([count, '[{} até {}]'.format(format_(periodo['inicio']), format_(periodo['fim']))],)
                count += 1
            initial = 0
        return initial, lista_combo

    def clean(self):
        cleaned_data = super().clean()
        tamanho_maximo_permitido = 2 * 1024 * 1024
        relatorio = self.cleaned_data.get('relatorio', None)
        if relatorio and relatorio.size > tamanho_maximo_permitido:
            raise forms.ValidationError({'relatorio': 'Tamanho máximo permitido 2MB.'})
        #
        del_atributos = []
        for atividade in self.instance.pratica_profissional.atividade_set.all():
            key_realizada = f'{atividade.pk}.realizada'
            key_motivo = f'{atividade.pk}.nao_realizada_motivo'
            key_motivo_descricao = f'{atividade.pk}.nao_realizada_motivo_descricao'
            #
            realizada = int(cleaned_data.get(key_realizada))
            try:
                motivo = int(cleaned_data.get(key_motivo))
            except Exception:
                motivo = None
            motivo_descricao = cleaned_data.get(key_motivo_descricao)
            #
            if realizada not in [choice[0] for choice in RelatorioSemestralEstagioAtividade.REALIZADA_CHOICES]:
                self._errors[key_realizada] = self.error_class(['Selecione uma opção válida.'])
                del_atributos.append(key_realizada)
            else:
                is_realizada = realizada == RelatorioSemestralEstagioAtividade.REALIZADA_SIM
                if is_realizada:
                    cleaned_data[key_motivo] = None
                    cleaned_data[key_motivo_descricao] = ''
                else:
                    if motivo not in [choice[0] for choice in RelatorioSemestralEstagioAtividade.NAO_REALIZADA_MOTIVO_CHOICES]:
                        self._errors[key_motivo] = self.error_class(['Selecione uma opção válida.'])
                        del_atributos.append(key_motivo)
                    elif motivo == RelatorioSemestralEstagioAtividade.NAO_REALIZADA_MOTIVO_OUTRO_MOTIVO and not motivo_descricao:
                        self._errors[key_motivo_descricao] = self.error_class(['Descreva o motivo.'])
                        del_atributos.append(key_motivo_descricao)
        for del_atributo in del_atributos:
            del self.cleaned_data[del_atributo]
        if 'periodo' not in self.cleaned_data or self.cleaned_data['periodo'] == '0':
            raise forms.ValidationError({'periodo': 'Selecione um período'})

        return cleaned_data

    @transaction.atomic
    def save(self, *args, **kwargs):

        if self.instance.pk:
            relatorio_semestral = super().save(*args, **kwargs)

            for atividade in relatorio_semestral.pratica_profissional.atividade_set.all():
                realizada = self.cleaned_data[f'{atividade.pk}.realizada']
                nao_realizada_motivo = self.cleaned_data[f'{atividade.pk}.nao_realizada_motivo']
                nao_realizada_motivo_descricao = self.cleaned_data[f'{atividade.pk}.nao_realizada_motivo_descricao']
                if relatorio_semestral.relatoriosemestralestagioatividade_set.filter(atividade=atividade).exists():
                    avaliacao_da_atividade = self.instance.relatoriosemestralestagioatividade_set.get(atividade=atividade)
                    avaliacao_da_atividade.realizada = realizada
                    avaliacao_da_atividade.nao_realizada_motivo = nao_realizada_motivo
                    avaliacao_da_atividade.nao_realizada_motivo_descricao = nao_realizada_motivo_descricao
                    avaliacao_da_atividade.save()
        else:
            periodo_selecionado = int(self.cleaned_data['periodo'])
            count = 1
            for periodo in self.instance.pratica_profissional.get_periodos_semestrais():
                if periodo_selecionado == count:
                    inicio = periodo['inicio']
                    fim = periodo['fim']
                    break
                count += 1
            self.instance.inicio = inicio
            self.instance.fim = fim

            relatorio_semestral = super().save(*args, **kwargs)

            for atividade in relatorio_semestral.pratica_profissional.atividade_set.all():
                realizada = self.cleaned_data[f'{atividade.pk}.realizada']
                nao_realizada_motivo = self.cleaned_data[f'{atividade.pk}.nao_realizada_motivo']
                nao_realizada_motivo_descricao = self.cleaned_data[f'{atividade.pk}.nao_realizada_motivo_descricao']
                avaliacao_da_atividade = RelatorioSemestralEstagioAtividade(
                    relatorio_semestral=relatorio_semestral,
                    atividade=atividade,
                    realizada=realizada,
                    nao_realizada_motivo=nao_realizada_motivo,
                    nao_realizada_motivo_descricao=nao_realizada_motivo_descricao,
                )
                avaliacao_da_atividade.save()
        #
        relatorio_semestral.pratica_profissional.save()
        #
        return relatorio_semestral


class RelatorioSemestralPreenchidoSupervisorForm(RelatorioSemestralEstagioForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fieldsets = ('Identificação do Aluno', {'fields': ('tipo', 'matricula_aluno', 'codigo_verificador')}), +self.fieldsets


class OfertaPraticaProfissionalForm(forms.ModelFormPlus):

    uo = forms.ModelMultiplePopupChoiceField(UnidadeOrganizacional.objects.suap().all(), label='Campus', required=False)
    cursos = forms.MultipleModelChoiceField(
        CursoCampus.objects,
        label='Cursos Alvo da Oferta',
        required=False,
        widget=AutocompleteWidget(multiple=True, search_fields=CursoCampus.SEARCH_FIELDS, form_filters=[('uo', 'diretoria__setor__uo__in')]),
    )

    class Meta:
        model = OfertaPraticaProfissional
        fields = (
            'concedente',
            'data_inicio',
            'data_fim',
            'qtd_vagas',
            'uo',
            'cursos',
            'a_partir_do_periodo',
            'turno',
            'ch_semanal',
            'folder',
            'habilidades',
            'descricao_atividades',
            'observacoes',
        )

    fieldsets = (
        ('Dados Gerais', {'fields': ('concedente', 'data_inicio', 'data_fim')}),
        ('Direcionamento da Oferta', {'fields': ('tipo_oferta', 'qtd_vagas', 'uo', 'cursos', 'a_partir_do_periodo', 'turno')}),
        ('Carga Horária', {'fields': ('ch_semanal',)}),
        ('Outras Informações', {'fields': ('folder', 'habilidades', 'descricao_atividades', 'observacoes')}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = self.fields['cursos'].queryset
        qs = qs.filter(modalidade__in=Modalidade.modalidades_que_fazem_estagio(), ativo=True).distinct()
        self.fields['cursos'].queryset = qs


class VisitaPraticaProfissionalForm(forms.ModelFormPlus):
    class Meta:
        model = VisitaPraticaProfissional
        exclude = ('pratica_profissional', 'orientador', 'ultimo_editor')

    fieldsets = (
        ('Dados Gerais', {'fields': ('data_visita',)}),
        (
            'Parecer da Visita',
            {
                'fields': (
                    ('ambiente_adequado', 'ambiente_adequado_justifique'),  # a)  # a)justifique
                    'desenvolvendo_atividades_previstas',  # b)
                    'desenvolvendo_atividades_fora_competencia',  # c)
                    ('desenvolvendo_atividades_nao_previstas', 'atividades_nao_previstas'),  # d)  # d descricao
                    'apoiado_pelo_supervidor',  # e)
                    ('direitos_respeitados', 'direitos_respeitados_especificar'),  # f)
                    'aprendizagem_satisfatoria',  # g)
                    'informacoes_adicionais',
                )  # sem letra
            },
        ),
        ('Relatório', {'fields': ('relatorio',)}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data_visita'].help_text = 'O estágio tem {} períodos trimestrais e deve ' 'ser submetido um relatório para cada período. Períodos: <br>'.format(
            self.instance.pratica_profissional.get_qtd_trimestres()
        )
        count = 1
        for trimestre in self.instance.pratica_profissional.get_periodos_trimestrais():
            visitas = self.instance.pratica_profissional.visitapraticaprofissional_set.filter(data_visita__range=(trimestre['inicio'], trimestre['fim']))
            self.fields['data_visita'].help_text = self.fields['data_visita'].help_text + '{}º De {} até {}. Visitas já cadastradas: {}\n'.format(
                count, format_(trimestre['inicio']), format_(trimestre['fim']), visitas.exists() and (', '.join([str(i) for i in visitas])) or 'Nenhuma visita neste período.'
            )
            count += 1
        self.fields['data_visita'].help_text = '<pre>' + self.fields['data_visita'].help_text + '</pre>'
        self.fields['relatorio'].required = False

    def clean(self):
        super().clean()
        desenvolvendo_atividades_nao_previstas = self.cleaned_data.get('desenvolvendo_atividades_nao_previstas')
        if desenvolvendo_atividades_nao_previstas == True and not self.cleaned_data.get('atividades_nao_previstas'):
            raise forms.ValidationError(
                {'atividades_nao_previstas': 'Foi marcado que o estagiário está desenvolvendo ' 'Atividades Não Previstas, neste caso estas ' 'devem ser especificadas.'}
            )
        if self.cleaned_data.get('data_visita') and self.cleaned_data.get('data_visita') > datetime.date.today():
            raise forms.ValidationError({'data_visita': 'Data no futuro: somente devem ser registradas visitas já ocorridas.'})
        if (
            self.cleaned_data.get('data_visita')
            and not self.instance.pratica_profissional.data_inicio <= self.cleaned_data.get('data_visita') <= self.instance.pratica_profissional.data_prevista_fim
        ):
            raise forms.ValidationError({'data_visita': 'Data não compreendida no intervalo da data de início à data prevista para o fim deste estágio.'})
        return self.cleaned_data


class VisitaAprendizagemForm(forms.ModelFormPlus):
    class Meta:
        model = VisitaAprendizagem
        exclude = ('aprendizagem', 'modulo_aprendizagem', 'orientador', 'ultimo_editor')

    fieldsets = (
        ('Dados Gerais', {'fields': ('data_visita',)}),
        (
            'Parecer da Visita',
            {
                'fields': (
                    ('ambiente_adequado', 'ambiente_adequado_justifique'),  # a)  # a)justifique
                    'desenvolvendo_atividades_previstas',  # b)
                    'desenvolvendo_atividades_fora_competencia',  # c)
                    ('desenvolvendo_atividades_nao_previstas', 'atividades_nao_previstas'),  # d)  # d descricao
                    'apoiado_pelo_supervidor',  # e)
                    ('direitos_respeitados', 'direitos_respeitados_especificar'),  # f)
                    'aprendizagem_satisfatoria',  # g)
                    'informacoes_adicionais',
                )  # sem letra
            },
        ),
        ('Relatório', {'fields': ('relatorio',)}),
    )

    def clean(self):
        cleaned_data = super().clean()
        if 'data_visita' not in cleaned_data:
            raise forms.ValidationError({'data_visita': 'Informe a data da visita.'})
        if self.cleaned_data.get('data_visita') and self.cleaned_data.get('data_visita') > datetime.date.today():
            raise forms.ValidationError({'data_visita': 'Data no futuro: somente devem ser registradas visitas já ocorridas.'})
        if not self.instance.aprendizagem.moduloaprendizagem_set.filter(inicio__lte=cleaned_data.get('data_visita'), fim__gte=cleaned_data.get('data_visita')).exists():
            raise forms.ValidationError({'data_visita': 'A data da visita deve estar compreendida entre a data de início e a de fim de algum dos módulos.'})
        desenvolvendo_atividades_nao_previstas = self.cleaned_data.get('desenvolvendo_atividades_nao_previstas')
        if desenvolvendo_atividades_nao_previstas == True and not self.cleaned_data.get('atividades_nao_previstas'):
            raise forms.ValidationError(
                {'atividades_nao_previstas': 'Foi marcado que o estagiário está desenvolvendo ' 'Atividades Não Previstas, neste caso estas ' 'devem ser especificadas.'}
            )

        return self.cleaned_data

    def save(self, *args, **kwargs):
        self.instance.ultimo_editor = self.request.user
        return super().save(*args, **kwargs)


class AvaliarRelatorioSemestralForm(forms.ModelFormPlus):
    class Meta:
        model = RelatorioSemestralEstagio
        fields = ('inicio', 'fim')


class OrientacaoEstagioForm(forms.ModelFormPlus):
    class Meta:
        model = OrientacaoEstagio
        exclude = ('pratica_profissional', 'orientador')

    def __init__(self, pratica_profissional, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.pratica_profissional = pratica_profissional
        self.instance.orientador = pratica_profissional.orientador
        self.instance.user = self.request.user


class OrientacaoAtividadeProfissionalEfetivaForm(forms.ModelFormPlus):
    class Meta:
        model = OrientacaoAtividadeProfissionalEfetiva
        exclude = ('atividade_profissional_efetiva', 'orientador')

    def __init__(self, atividade_profissional_efetiva, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.atividade_profissional_efetiva = atividade_profissional_efetiva
        self.instance.orientador = atividade_profissional_efetiva.orientador
        self.instance.user = self.request.user


class OrientacaoAprendizagemForm(forms.ModelFormPlus):
    class Meta:
        model = OrientacaoAprendizagem
        exclude = ('aprendizagem', 'orientador')

    def __init__(self, aprendizagem, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.aprendizagem = aprendizagem
        self.instance.orientador = aprendizagem.orientador
        self.instance.user = self.request.user


class EncontrarEstagioForm(forms.FormPlus):
    METHOD = 'GET'
    email_supervisor = forms.EmailField(label='E-mail do Supervisor', required=True)
    codigo_verificador = forms.CharField(label='Código Verificador', required=True)
    matricula = forms.CharField(label='Matrícula do Aluno', required=True)
    recaptcha = ReCaptchaField(label='')


class EncontrarAprendizagemForm(forms.FormPlus):
    METHOD = 'GET'
    email_monitor = forms.EmailField(label='E-mail do Monitor', required=True)
    codigo_verificador = forms.CharField(label='Código Verificador', required=True)
    matricula = forms.CharField(label='Matrícula do Aluno', required=True)
    inicio = forms.DateFieldPlus(label='Data de Início do Módulo Avaliado', required=True)
    fim = forms.DateFieldPlus(label='Data de Fim do Módulo Avaliado', required=True)


class AprendizagemForm(forms.ModelFormPlus):
    vinculo = forms.ModelChoiceFieldPlus(queryset=Vinculo.objects.servidores(), widget=AutocompleteWidget(search_fields=Vinculo.SEARCH_FIELDS), label='Orientador', required=True)
    estado = forms.ModelChoiceField(queryset=Estado.objects, label='Unidade da Federação', widget=Select())
    cidade = forms.ModelChoiceFieldPlus(
        Cidade.objects, label='Município', required=True, widget=AutocompleteWidget(search_fields=Cidade.SEARCH_FIELDS, form_filters=[('estado', 'estado__in')])
    )
    confirmacao_aprendizagem_eh_remunerada = forms.BooleanField(
        label='Senhor Coordenador de Estágio favor confirmar que esta aprendizagem é remunerada.',
        help_text='A aprendizagem sempre é remunerada por exigência legal, se esta não tem remuneração, o ' 'problema deve ser sanado antes de ser feito o cadastro.',
    )

    descricao_atividades_1 = forms.CharField(
        label='Descrição das Atividades do Módulo', required=False, widget=forms.Textarea(), help_text='Estas atividades serão utilizadas para as avaliações do módulo.'
    )
    data_inicio_1 = forms.DateFieldPlus(label='Data de Início do Módulo', required=False)
    data_fim_1 = forms.DateFieldPlus(label='Data de Fim do Módulo', required=False)
    ch_teorica_semanal_1 = forms.IntegerFieldPlus(label='Carga Horária Teórica Semanal', required=False)
    ch_pratica_semanal_1 = forms.IntegerFieldPlus(label='Carga Horária Prática Semanal', required=False)

    descricao_atividades_2 = forms.CharField(
        label='Descrição das Atividades do Módulo', required=False, widget=forms.Textarea(), help_text='Estas atividades serão utilizadas para as avaliações do módulo.'
    )
    data_inicio_2 = forms.DateFieldPlus(label='Data de Início do Módulo', required=False)
    data_fim_2 = forms.DateFieldPlus(label='Data de Fim do Módulo', required=False)
    ch_teorica_semanal_2 = forms.IntegerFieldPlus(label='Carga Horária Teórica Semanal', required=False)
    ch_pratica_semanal_2 = forms.IntegerFieldPlus(label='Carga Horária Prática Semanal', required=False)

    descricao_atividades_3 = forms.CharField(
        label='Descrição das Atividades do Módulo', required=False, widget=forms.Textarea(), help_text='Estas atividades serão utilizadas para as avaliações do módulo.'
    )
    data_inicio_3 = forms.DateFieldPlus(label='Data de Início do Módulo', required=False)
    data_fim_3 = forms.DateFieldPlus(label='Data de Fim do Módulo', required=False)
    ch_teorica_semanal_3 = forms.IntegerFieldPlus(label='Carga Horária Teórica Semanal', required=False)
    ch_pratica_semanal_3 = forms.IntegerFieldPlus(label='Carga Horária Prática Semanal', required=False)

    descricao_atividades_4 = forms.CharField(
        label='Descrição das Atividades do Módulo', required=False, widget=forms.Textarea(), help_text='Estas atividades serão utilizadas para as avaliações do módulo.'
    )
    data_inicio_4 = forms.DateFieldPlus(label='Data de Início do Módulo', required=False)
    data_fim_4 = forms.DateFieldPlus(label='Data de Fim do Módulo', required=False)
    ch_teorica_semanal_4 = forms.IntegerFieldPlus(label='Carga Horária Teórica Semanal', required=False)
    ch_pratica_semanal_4 = forms.IntegerFieldPlus(label='Carga Horária Prática Semanal', required=False)

    emails_relatorio_frequencia = forms.MultiEmailField(
        label='E-mails para Envio do Relatório de Frequência',
        help_text='Informe o(s) e-mail(s), separados por virgula, para o(s) quais será enviado o relatório de '
        'frequência do aprendiz. Não utilize espaços. Exemplo: rh@empresa.com.br,coordenador_estagio@ifrn.edu.br,'
        'monitor@empresa.com.br',
        required=False,
    )

    email_monitor = forms.EmailField(required=True, help_text='Este e-mail será importante para o envio da avaliação.', label='E-mail')

    class Meta:
        model = Aprendizagem
        exclude = (
            'data_encerramento',
            'encerramento_por',
            'motivo_encerramento',
            'motivacao_rescisao',
            'data_encerramento',
            'ch_final',
            'laudo_avaliacao',
            'orientador',
            'eh_utilizado_como_pratica_profissional',
            'plano_atividades',
        )

    class Media:
        js = ('/static/estagios/js/AprendizagemForm.js',)

    fieldsets = (
        ('Dados Gerais', {'fields': ('aprendiz', 'convenio', 'turno', 'empresa', 'vinculo')}),
        ('Endereço do Estabelecimento da Concedente', {'fields': ('estado', 'cidade', 'logradouro', 'numero', 'complemento', 'bairro', 'cep')}),
        ('Remuneração', {'fields': ('confirmacao_aprendizagem_eh_remunerada', 'auxilio_transporte', 'outros_beneficios', 'descricao_outros_beneficios')}),
        ('Documentação', {'fields': ('contrato_aprendizagem', 'carteira_trabalho', 'resumo_curso')}),
        ('Empregado Monitor', {'fields': ('nome_monitor', 'telefone_monitor', 'cargo_monitor', 'email_monitor', 'observacao')}),
        (
            'Configuração para Envio de Relatório de Frequência',
            {
                'fields': (
                    'periodicidade_envio_relatorio_frequencia',
                    ('inicio_periodo_frequencia_1', 'fim_periodo_frequencia_1'),
                    ('inicio_periodo_frequencia_2', 'fim_periodo_frequencia_2'),
                    'emails_relatorio_frequencia',
                )
            },
        ),
        ('Módulo I', {'fields': ('modulo_1', 'descricao_atividades_1', 'data_inicio_1', 'data_fim_1', 'ch_teorica_semanal_1', 'ch_pratica_semanal_1')}),
        ('Módulo II', {'fields': ('modulo_2', 'descricao_atividades_2', 'data_inicio_2', 'data_fim_2', 'ch_teorica_semanal_2', 'ch_pratica_semanal_2')}),
        ('Módulo III', {'fields': ('modulo_3', 'descricao_atividades_3', 'data_inicio_3', 'data_fim_3', 'ch_teorica_semanal_3', 'ch_pratica_semanal_3')}),
        ('Módulo IV', {'fields': ('modulo_4', 'descricao_atividades_4', 'data_inicio_4', 'data_fim_4', 'ch_teorica_semanal_4', 'ch_pratica_semanal_4')}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['aprendiz'].widget = AutocompleteWidget(search_fields=Aluno.SEARCH_FIELDS)
        self.fields['convenio'].widget = AutocompleteWidget(search_fields=Convenio.SEARCH_FIELDS)
        self.fields['convenio'].queryset = self.fields['convenio'].queryset.all()
        self.fields['empresa'].widget = AutocompleteWidget(search_fields=PessoaJuridica.SEARCH_FIELDS)
        self.fields['empresa'].queryset = self.fields['empresa'].queryset.all()
        if self.instance.pk and self.instance.orientador:
            try:
                self.fields['vinculo'].initial = self.instance.orientador.vinculo
            except Exception:
                pass

        if in_group(self.request.user, ['Coordenador de Estágio']) and not in_group(self.request.user, ['Coordenador de Estágio Sistêmico', 'estagios Administrador']):
            self.fields['aprendiz'].queryset = self.fields['aprendiz'].queryset.filter(matriz__isnull=False, curso_campus__diretoria__setor__uo=get_uo(self.request.user))
        else:
            self.fields['aprendiz'].queryset = self.fields['aprendiz'].queryset.filter(matriz__isnull=False)

        if self.instance.pk and self.instance.cidade:
            self.fields['estado'].initial = self.instance.cidade.estado

        if self.instance.pk:
            self.fields['confirmacao_aprendizagem_eh_remunerada'].initial = True
            if self.instance.modulo_1:
                modulo_1 = self.instance.moduloaprendizagem_set.filter(tipo_modulo=ModuloAprendizagem.MODULO_I)[0]
                self.fields['descricao_atividades_1'].initial = modulo_1.atividades
                self.fields['data_inicio_1'].initial = modulo_1.inicio
                self.fields['data_fim_1'].initial = modulo_1.fim
                self.fields['ch_teorica_semanal_1'].initial = modulo_1.ch_teorica_semanal
                self.fields['ch_pratica_semanal_1'].initial = modulo_1.ch_pratica_semanal
            if self.instance.modulo_2:
                modulo_2 = self.instance.moduloaprendizagem_set.filter(tipo_modulo=ModuloAprendizagem.MODULO_II)[0]
                self.fields['descricao_atividades_2'].initial = modulo_2.atividades
                self.fields['data_inicio_2'].initial = modulo_2.inicio
                self.fields['data_fim_2'].initial = modulo_2.fim
                self.fields['ch_teorica_semanal_2'].initial = modulo_2.ch_teorica_semanal
                self.fields['ch_pratica_semanal_2'].initial = modulo_2.ch_pratica_semanal
            if self.instance.modulo_3:
                modulo_3 = self.instance.moduloaprendizagem_set.filter(tipo_modulo=ModuloAprendizagem.MODULO_III)[0]
                self.fields['descricao_atividades_3'].initial = modulo_3.atividades
                self.fields['data_inicio_3'].initial = modulo_3.inicio
                self.fields['data_fim_3'].initial = modulo_3.fim
                self.fields['ch_teorica_semanal_3'].initial = modulo_3.ch_teorica_semanal
                self.fields['ch_pratica_semanal_3'].initial = modulo_3.ch_pratica_semanal
            if self.instance.modulo_4:
                modulo_4 = self.instance.moduloaprendizagem_set.filter(tipo_modulo=ModuloAprendizagem.MODULO_IV)[0]
                self.fields['descricao_atividades_4'].initial = modulo_4.atividades
                self.fields['data_inicio_4'].initial = modulo_4.inicio
                self.fields['data_fim_4'].initial = modulo_4.fim
                self.fields['ch_teorica_semanal_4'].initial = modulo_4.ch_teorica_semanal
                self.fields['ch_pratica_semanal_4'].initial = modulo_4.ch_pratica_semanal

    def clean(self):
        cleaned_data = super().clean()

        del_atributos = []

        if not cleaned_data.get('modulo_1', None) and not cleaned_data.get('modulo_2', None) and not cleaned_data.get('modulo_3', None) and not cleaned_data.get('modulo_4', None):
            raise forms.ValidationError('Deve ser cadastrado pelo menos um módulo para a aprendizagem.')

        if cleaned_data.get('modulo_1', None):
            if not cleaned_data.get('descricao_atividades_1', None):
                self._errors['descricao_atividades_1'] = self.error_class(['É necessária uma descrição.'])
                del_atributos.append('descricao_atividades_1')
            if not cleaned_data.get('data_inicio_1', None):
                self._errors['data_inicio_1'] = self.error_class(['É necessária uma data de início.'])
                del_atributos.append('data_inicio_1')
            if not cleaned_data.get('data_fim_1', None):
                self._errors['data_fim_1'] = self.error_class(['É necessária uma data de fim.'])
                del_atributos.append('data_fim_1')
            if not cleaned_data.get('ch_teorica_semanal_1', None):
                self._errors['ch_teorica_semanal_1'] = self.error_class(['É necessária uma carga horária teórica semanal.'])
                del_atributos.append('ch_teorica_semanal_1')
            if not cleaned_data.get('ch_pratica_semanal_1', None):
                self._errors['ch_pratica_semanal_1'] = self.error_class(['É necessária uma carga horária prática semanal.'])
                del_atributos.append('ch_pratica_semanal_1')

        if cleaned_data.get('modulo_2', None):
            if not cleaned_data.get('descricao_atividades_2', None):
                self._errors['descricao_atividades_2'] = self.error_class(['É necessária uma descrição.'])
                del_atributos.append('descricao_atividades_2')
            if not cleaned_data.get('data_inicio_2', None):
                self._errors['data_inicio_2'] = self.error_class(['É necessária uma data de início.'])
                del_atributos.append('data_inicio_2')
            if not cleaned_data.get('data_fim_2', None):
                self._errors['data_fim_2'] = self.error_class(['É necessária uma data de fim.'])
                del_atributos.append('data_fim_2')
            if not cleaned_data.get('ch_teorica_semanal_2', None):
                self._errors['ch_teorica_semanal_2'] = self.error_class(['É necessária uma carga horária teórica semanal.'])
                del_atributos.append('ch_teorica_semanal_2')
            if not cleaned_data.get('ch_pratica_semanal_2', None):
                self._errors['ch_pratica_semanal_2'] = self.error_class(['É necessária uma carga horária prática semanal.'])
                del_atributos.append('ch_pratica_semanal_2')

        if cleaned_data.get('modulo_3', None):
            if not cleaned_data.get('descricao_atividades_3', None):
                self._errors['descricao_atividades_3'] = self.error_class(['É necessária uma descrição.'])
                del_atributos.append('descricao_atividades_3')
            if not cleaned_data.get('data_inicio_3', None):
                self._errors['data_inicio_3'] = self.error_class(['É necessária uma data de início.'])
                del_atributos.append('data_inicio_3')
            if not cleaned_data.get('data_fim_3', None):
                self._errors['data_fim_3'] = self.error_class(['É necessária uma data de fim.'])
                del_atributos.append('data_fim_3')
            if not cleaned_data.get('ch_teorica_semanal_3', None):
                self._errors['ch_teorica_semanal_3'] = self.error_class(['É necessária uma carga horária teórica semanal.'])
                del_atributos.append('ch_teorica_semanal_3')
            if not cleaned_data.get('ch_pratica_semanal_3', None):
                self._errors['ch_pratica_semanal_3'] = self.error_class(['É necessária uma carga horária prática semanal.'])
                del_atributos.append('ch_pratica_semanal_3')

        if cleaned_data.get('modulo_4', None):
            if not cleaned_data.get('descricao_atividades_4', None):
                self._errors['descricao_atividades_4'] = self.error_class(['É necessária uma descrição.'])
                del_atributos.append('descricao_atividades_4')
            if not cleaned_data.get('data_inicio_4', None):
                self._errors['data_inicio_4'] = self.error_class(['É necessária uma data de início.'])
                del_atributos.append('data_inicio_4')
            if not cleaned_data.get('data_fim_4', None):
                self._errors['data_fim_4'] = self.error_class(['É necessária uma data de fim.'])
                del_atributos.append('data_fim_4')
            if not cleaned_data.get('ch_teorica_semanal_4', None):
                self._errors['ch_teorica_semanal_4'] = self.error_class(['É necessária uma carga horária teórica semanal.'])
                del_atributos.append('ch_teorica_semanal_4')
            if not cleaned_data.get('ch_pratica_semanal_4', None):
                self._errors['ch_pratica_semanal_4'] = self.error_class(['É necessária uma carga horária prática semanal.'])
                del_atributos.append('ch_pratica_semanal_4')

        datas = list()
        if cleaned_data.get('modulo_1', None):
            if cleaned_data.get('data_inicio_1', None):
                datas.append(cleaned_data.get('data_inicio_1', None))
            if cleaned_data.get('data_fim_1', None):
                datas.append(cleaned_data.get('data_fim_1', None))
                if cleaned_data.get('data_inicio_1', None) and cleaned_data.get('data_inicio_1', None) >= cleaned_data.get('data_fim_1', None):
                    raise forms.ValidationError({'data_inicio_1': 'A data de início deve ser menor que a data de fim do módulo.'})
        if cleaned_data.get('modulo_2', None):
            if cleaned_data.get('data_inicio_2', None):
                datas.append(cleaned_data.get('data_inicio_2', None))
            if cleaned_data.get('data_fim_2', None):
                datas.append(cleaned_data.get('data_fim_2', None))
                if cleaned_data.get('data_inicio_2', None) and cleaned_data.get('data_inicio_2', None) >= cleaned_data.get('data_fim_2', None):
                    raise forms.ValidationError({'data_inicio_2': 'A data de início deve ser menor que a data de fim do módulo.'})
        if cleaned_data.get('modulo_3', None):
            if cleaned_data.get('data_inicio_3', None):
                datas.append(cleaned_data.get('data_inicio_3', None))
            if cleaned_data.get('data_fim_3', None):
                datas.append(cleaned_data.get('data_fim_3', None))
                if cleaned_data.get('data_inicio_3', None) and cleaned_data.get('data_inicio_3', None) >= cleaned_data.get('data_fim_3', None):
                    raise forms.ValidationError({'data_inicio_3': 'A data de início deve ser menor que a data de fim do módulo.'})
        if cleaned_data.get('modulo_4', None):
            if cleaned_data.get('data_inicio_4', None):
                datas.append(cleaned_data.get('data_inicio_4', None))
            if cleaned_data.get('data_fim_4', None):
                datas.append(cleaned_data.get('data_fim_4', None))
                if cleaned_data.get('data_inicio_4', None) and cleaned_data.get('data_inicio_4', None) >= cleaned_data.get('data_fim_4', None):
                    raise forms.ValidationError({'data_inicio_4': 'A data de início deve ser menor que a data de fim do módulo.'})

        data_anterior = datetime.date.today() - relativedelta(years=100)
        for data in datas:
            if data > data_anterior:
                data_anterior = data
            else:
                raise forms.ValidationError(
                    'Datas inconsistentes. A data de cada módulo início deve ser '
                    'menor que a data de fim. A data de início de módulos numericamente '
                    'maiores deve ser maior que a data de fim dos módulos anteriores.'
                )

        for del_atributo in del_atributos:
            if self.cleaned_data.get(del_atributo):
                del self.cleaned_data[del_atributo]

        # verificação dos campos de Configuração para Envio de Relatório de Frequência
        periodicidade_envio_relatorio_frequencia = self.cleaned_data.get('periodicidade_envio_relatorio_frequencia')
        inicio_periodo_frequencia_1 = self.cleaned_data.get('inicio_periodo_frequencia_1')
        fim_periodo_frequencia_1 = self.cleaned_data.get('fim_periodo_frequencia_1')
        inicio_periodo_frequencia_2 = self.cleaned_data.get('inicio_periodo_frequencia_2')
        fim_periodo_frequencia_2 = self.cleaned_data.get('fim_periodo_frequencia_2')
        emails_relatorio_frequencia = self.cleaned_data.get('emails_relatorio_frequencia')
        del_atributos = []
        if periodicidade_envio_relatorio_frequencia is None:
            if inicio_periodo_frequencia_1 or fim_periodo_frequencia_1 or inicio_periodo_frequencia_2 or fim_periodo_frequencia_2:
                self._errors['periodicidade_envio_relatorio_frequencia'] = self.error_class(
                    ['Só é possível definir período de apuração de frequência se a periodicidade de envio também estiver definida.']
                )
                del_atributos.append('periodicidade_envio_relatorio_frequencia')
        elif periodicidade_envio_relatorio_frequencia == Aprendizagem.MENSAL:
            if not inicio_periodo_frequencia_1:
                self._errors['inicio_periodo_frequencia_1'] = self.error_class(
                    ['Se a periodicidade de envio do relatório de frequência é mensal, é necessário preencher este campo.']
                )
                del_atributos.append('inicio_periodo_frequencia_1')
            if not fim_periodo_frequencia_1:
                self._errors['fim_periodo_frequencia_1'] = self.error_class(['Se a periodicidade de envio do relatório de frequência é mensal, é necessário preencher este campo.'])
                del_atributos.append('fim_periodo_frequencia_1')
            elif not (inicio_periodo_frequencia_1 == 1 and fim_periodo_frequencia_1 == 31) and not (
                inicio_periodo_frequencia_1 >= 2 and fim_periodo_frequencia_1 == inicio_periodo_frequencia_1 - 1
            ):
                self._errors['fim_periodo_frequencia_1'] = self.error_class(
                    [
                        'Se o início do período é no dia 1, o final do período necessariamente será no dia 31. '
                        'Se, por exemplo, o início do período é no dia 2, o fim do período necessariamente será '
                        'no dia 1. Se, por exemplo, o início do período é no dia 3, o fim do período necessariamente '
                        'será no dia 2. E assim sucessivamente.'
                    ]
                )
                del_atributos.append('fim_periodo_frequencia_1')
            if inicio_periodo_frequencia_2:
                self._errors['inicio_periodo_frequencia_2'] = self.error_class(
                    ['Se a periodicidade de envio do relatório de frequência é mensal, este campo deve ser deixado em branco.']
                )
                del_atributos.append('inicio_periodo_frequencia_2')
            if fim_periodo_frequencia_2:
                self._errors['fim_periodo_frequencia_2'] = self.error_class(
                    ['Se a periodicidade de envio do relatório de frequência é mensal, este campo deve ser deixado em branco.']
                )
                del_atributos.append('fim_periodo_frequencia_2')
        elif periodicidade_envio_relatorio_frequencia == Aprendizagem.QUINZENAL:
            if not inicio_periodo_frequencia_1:
                self._errors['inicio_periodo_frequencia_1'] = self.error_class(
                    ['Se a periodicidade de envio do relatório de frequência é quinzenal, é necessário preencher este campo.']
                )
                del_atributos.append('inicio_periodo_frequencia_1')
            if not fim_periodo_frequencia_1:
                self._errors['fim_periodo_frequencia_1'] = self.error_class(
                    ['Se a periodicidade de envio do relatório de frequência é quinzenal, é necessário preencher este campo.']
                )
                del_atributos.append('fim_periodo_frequencia_1')

            if not inicio_periodo_frequencia_2:
                self._errors['inicio_periodo_frequencia_2'] = self.error_class(
                    ['Se a periodicidade de envio do relatório de frequência é quinzenal, é necessário preencher este campo.']
                )
                del_atributos.append('inicio_periodo_frequencia_2')
            if not fim_periodo_frequencia_2:
                self._errors['fim_periodo_frequencia_2'] = self.error_class(
                    ['Se a periodicidade de envio do relatório de frequência é quinzenal, é necessário preencher este campo.']
                )
                del_atributos.append('fim_periodo_frequencia_2')
            if inicio_periodo_frequencia_1 and fim_periodo_frequencia_1 and inicio_periodo_frequencia_2 and fim_periodo_frequencia_2:
                periodo_1 = self.conjunto_dias(inicio_periodo_frequencia_1, fim_periodo_frequencia_1)
                periodo_2 = self.conjunto_dias(inicio_periodo_frequencia_2, fim_periodo_frequencia_2)
                if len(periodo_1) < 14:
                    self._errors['fim_periodo_frequencia_1'] = self.error_class(['O primeiro período tem menos de 14 dias.'])
                    del_atributos.append('fim_periodo_frequencia_1')
                if len(periodo_1) > 17:
                    self._errors['fim_periodo_frequencia_1'] = self.error_class(['O primeiro período tem mais de 17 dias.'])
                    del_atributos.append('fim_periodo_frequencia_1')
                if len(periodo_2) < 14:
                    self._errors['fim_periodo_frequencia_2'] = self.error_class(['O segundo período tem menos de 14 dias.'])
                    del_atributos.append('fim_periodo_frequencia_2')
                if len(periodo_2) > 17:
                    self._errors['fim_periodo_frequencia_2'] = self.error_class(['O segundo período tem mais de 17 dias.'])
                    del_atributos.append('fim_periodo_frequencia_2')
                if not periodo_1.intersection(periodo_2).issubset(set()):
                    self._errors['fim_periodo_frequencia_2'] = self.error_class(['Os períodos então entrando um no outro. Eles devem ser conjuntos de dias disjuntos.'])
                    del_atributos.append('fim_periodo_frequencia_2')
                if not self.conjunto_dias(1, 31).issubset(periodo_1.union(periodo_2)):
                    self._errors['fim_periodo_frequencia_2'] = self.error_class(
                        ['Os períodos não estão cobrindo do dia 1 ao 31. A união dos conjuntos de dias dos períodos deve abranger todos estes dias.']
                    )
                    del_atributos.append('fim_periodo_frequencia_2')
        if not emails_relatorio_frequencia:
            if inicio_periodo_frequencia_1 or fim_periodo_frequencia_1 or inicio_periodo_frequencia_2 or fim_periodo_frequencia_2 or periodicidade_envio_relatorio_frequencia:
                self._errors['emails_relatorio_frequencia'] = self.error_class(['Para envio do relatório é essencial o cadastro de, no mínimo, um e-mail.'])
                del_atributos.append('emails_relatorio_frequencia')
        for del_atributo in del_atributos:
            if del_atributo in self.cleaned_data:
                del self.cleaned_data[del_atributo]

    def conjunto_dias(self, inicio, fim):
        if inicio < fim:
            return set(range(inicio, fim + 1))
        else:
            return set(list(range(inicio, 32)) + list(range(1, fim + 1)))

    @transaction.atomic
    def save(self, *args, **kwargs):
        vinculo = self.cleaned_data['vinculo']
        qs = Professor.objects.filter(vinculo__id=vinculo.id)
        if qs.exists():
            self.instance.orientador = qs[0]
        else:
            professor = Professor()
            professor.vinculo = vinculo
            professor.save()
            self.instance.orientador = professor
            Group.objects.get(name='Professor').user_set.add(professor.vinculo.user)
        self.instance.eh_utilizado_como_pratica_profissional = False
        aprendizagem = super().save()

        if self.cleaned_data.get('modulo_1', None):
            modulo_1 = self.instance.moduloaprendizagem_set.filter(tipo_modulo=ModuloAprendizagem.MODULO_I)
            if modulo_1.exists():
                modulo_1 = modulo_1[0]
            else:
                modulo_1 = None

            if not modulo_1:
                modulo_1 = ModuloAprendizagem(
                    tipo_modulo=ModuloAprendizagem.MODULO_I,
                    aprendizagem=aprendizagem,
                    atividades=self.cleaned_data.get('descricao_atividades_1', None),
                    inicio=self.cleaned_data.get('data_inicio_1', None),
                    fim=self.cleaned_data.get('data_fim_1', None),
                    ch_teorica_semanal=self.cleaned_data.get('ch_teorica_semanal_1', None),
                    ch_pratica_semanal=self.cleaned_data.get('ch_pratica_semanal_1', None),
                )
            else:
                modulo_1.atividades = self.cleaned_data.get('descricao_atividades_1', None)
                modulo_1.inicio = self.cleaned_data.get('data_inicio_1', None)
                modulo_1.fim = self.cleaned_data.get('data_fim_1', None)
                modulo_1.ch_teorica_semanal = self.cleaned_data.get('ch_teorica_semanal_1', None)
                modulo_1.ch_pratica_semanal = self.cleaned_data.get('ch_pratica_semanal_1', None)
            modulo_1.save()
        else:
            modulo_1 = self.instance.moduloaprendizagem_set.filter(tipo_modulo=ModuloAprendizagem.MODULO_I)
            if modulo_1.exists():
                modulo_1.delete()

        if self.cleaned_data.get('modulo_2', None):
            modulo_2 = self.instance.moduloaprendizagem_set.filter(tipo_modulo=ModuloAprendizagem.MODULO_II)
            if modulo_2.exists():
                modulo_2 = modulo_2[0]
            else:
                modulo_2 = None

            if not modulo_2:
                modulo_2 = ModuloAprendizagem(
                    tipo_modulo=ModuloAprendizagem.MODULO_II,
                    aprendizagem=aprendizagem,
                    atividades=self.cleaned_data.get('descricao_atividades_2', None),
                    inicio=self.cleaned_data.get('data_inicio_2', None),
                    fim=self.cleaned_data.get('data_fim_2', None),
                    ch_teorica_semanal=self.cleaned_data.get('ch_teorica_semanal_2', None),
                    ch_pratica_semanal=self.cleaned_data.get('ch_pratica_semanal_2', None),
                )
            else:
                modulo_2.atividades = self.cleaned_data.get('descricao_atividades_2', None)
                modulo_2.inicio = self.cleaned_data.get('data_inicio_2', None)
                modulo_2.fim = self.cleaned_data.get('data_fim_2', None)
                modulo_2.ch_teorica_semanal = self.cleaned_data.get('ch_teorica_semanal_2', None)
                modulo_2.ch_pratica_semanal = self.cleaned_data.get('ch_pratica_semanal_2', None)
            modulo_2.save()
        else:
            modulo_2 = self.instance.moduloaprendizagem_set.filter(tipo_modulo=ModuloAprendizagem.MODULO_II)
            if modulo_2.exists():
                modulo_2.delete()

        if self.cleaned_data.get('modulo_3', None):
            modulo_3 = self.instance.moduloaprendizagem_set.filter(tipo_modulo=ModuloAprendizagem.MODULO_III)
            if modulo_3.exists():
                modulo_3 = modulo_3[0]
            else:
                modulo_3 = None

            if not modulo_3:
                modulo_3 = ModuloAprendizagem(
                    tipo_modulo=ModuloAprendizagem.MODULO_III,
                    aprendizagem=aprendizagem,
                    atividades=self.cleaned_data.get('descricao_atividades_3', None),
                    inicio=self.cleaned_data.get('data_inicio_3', None),
                    fim=self.cleaned_data.get('data_fim_3', None),
                    ch_teorica_semanal=self.cleaned_data.get('ch_teorica_semanal_3', None),
                    ch_pratica_semanal=self.cleaned_data.get('ch_pratica_semanal_3', None),
                )
            else:
                modulo_3.atividades = self.cleaned_data.get('descricao_atividades_3', None)
                modulo_3.inicio = self.cleaned_data.get('data_inicio_3', None)
                modulo_3.fim = self.cleaned_data.get('data_fim_3', None)
                modulo_3.ch_teorica_semanal = self.cleaned_data.get('ch_teorica_semanal_3', None)
                modulo_3.ch_pratica_semanal = self.cleaned_data.get('ch_pratica_semanal_3', None)
            modulo_3.save()
        else:
            modulo_3 = self.instance.moduloaprendizagem_set.filter(tipo_modulo=ModuloAprendizagem.MODULO_III)
            if modulo_3.exists():
                modulo_3.delete()

        if self.cleaned_data.get('modulo_4', None):
            modulo_4 = self.instance.moduloaprendizagem_set.filter(tipo_modulo=ModuloAprendizagem.MODULO_IV)
            if modulo_4.exists():
                modulo_4 = modulo_4[0]
            else:
                modulo_4 = None

            if not modulo_4:
                modulo_4 = ModuloAprendizagem(
                    tipo_modulo=ModuloAprendizagem.MODULO_IV,
                    aprendizagem=aprendizagem,
                    atividades=self.cleaned_data.get('descricao_atividades_4', None),
                    inicio=self.cleaned_data.get('data_inicio_4', None),
                    fim=self.cleaned_data.get('data_fim_4', None),
                    ch_teorica_semanal=self.cleaned_data.get('ch_teorica_semanal_4', None),
                    ch_pratica_semanal=self.cleaned_data.get('ch_pratica_semanal_4', None),
                )
            else:
                modulo_4.atividades = self.cleaned_data.get('descricao_atividades_4', None)
                modulo_4.inicio = self.cleaned_data.get('data_inicio_4', None)
                modulo_4.fim = self.cleaned_data.get('data_fim_4', None)
                modulo_4.ch_teorica_semanal = self.cleaned_data.get('ch_teorica_semanal_4', None)
                modulo_4.ch_pratica_semanal = self.cleaned_data.get('ch_pratica_semanal_4', None)
            modulo_4.save()
        else:
            modulo_4 = self.instance.moduloaprendizagem_set.filter(tipo_modulo=ModuloAprendizagem.MODULO_IV)
            if modulo_4.exists():
                modulo_4.delete()

        notificar = not self.instance.pk
        returno = super().save(*args, **kwargs)
        if notificar:
            self.instance.notificar_professores_diarios(self.request.user)
            self.instance.enviar_email_empregado_monitor_recem_cadastrado(self.request.user)
            self.instance.enviar_email_aprendiz_recem_cadastrado(self.request.user)
            self.instance.enviar_email_orientador_recem_cadastrado(self.request.user)
        return returno


class AditivoContratualAprendizagemForm(forms.ModelFormPlus):
    # tipo 1 = orientador
    orientador = forms.ModelChoiceFieldPlus(Vinculo.objects.servidores(), label='Orientador', required=False)

    # tipo 3 = monitor
    nome_monitor = forms.CharFieldPlus(label='Nome', required=False)
    telefone_monitor = forms.CharFieldPlus(label='Telefone', required=False)
    cargo_monitor = forms.CharFieldPlus(label='Cargo', required=False)
    email_monitor = forms.EmailField(label='E-mail', required=False)
    observacao = forms.CharFieldPlus(label='Observação', required=False, widget=forms.Textarea())

    # tipo 4 = turno
    turno = forms.ModelChoiceField(Turno.objects.all(), label='Turno', required=False)

    # tipo 5 = filial (demanda 562)
    empresa = forms.ModelChoiceFieldPlus(label='Concedente', queryset=PessoaJuridica.objects, widget=AutocompleteWidget(search_fields=PessoaJuridica.SEARCH_FIELDS), required=False)
    cidade = forms.ModelChoiceFieldPlus(
        label='Município', queryset=Cidade.objects, widget=AutocompleteWidget(search_fields=Cidade.SEARCH_FIELDS, form_filters=[('estado', 'estado__in')]), required=False
    )
    logradouro = forms.CharField(label='Logradouro', required=False)
    numero = forms.CharField(label='Nº', required=False)
    complemento = forms.CharField(label='Complemento', required=False)
    bairro = forms.CharField(label='Bairro', required=False)
    cep = forms.CharField(label='CEP', required=False)
    controla_tempo = forms.CharFieldPlus(required=False, widget=forms.HiddenInput())

    class Meta:
        model = AditivoContratualAprendizagem
        fields = ('tipos_aditivo', 'descricao', 'aditivo', 'inicio_vigencia')

    class Media:
        js = ('/static/estagios/js/AditivoContratualAprendizagemForm.js',)

    fieldsets = (
        ('Dados Gerais', {'fields': ('tipos_aditivo', ('inicio_vigencia', 'aditivo'), 'descricao')}),
        ('Aditivo de Professor Orientador', {'fields': ('orientador',)}),
        ('Aditivo de Empregado Monitor', {'fields': ('nome_monitor', 'telefone_monitor', 'cargo_monitor', 'email_monitor', 'observacao')}),
        ('Aditivo de Horário', {'fields': ('turno',)}),
        ('Aditivo de Mudança de Filial', {'fields': ('empresa', 'cidade', 'logradouro', 'numero', 'complemento', 'bairro', 'cep')}),
    )

    def __init__(self, aprendizagem, *args, **kwargs):
        TipoAditivoAprendizagem.popula_tipos_aditivos()

        super().__init__(*args, **kwargs)

        # field 'tipos_aditivo'
        # o domínio são todos os tipos de aditivos, exceto o tipo 'Tempo'
        self.fields['tipos_aditivo'].widget = forms.CheckboxSelectMultiple()
        self.fields['tipos_aditivo'].queryset = TipoAditivoAprendizagem.objects.all().order_by('id')
        lista = list()
        for modulo in ModuloAprendizagem.objects.filter(aprendizagem=aprendizagem):
            self.fields[f'{modulo.id}_inicio'] = forms.DateFieldPlus(label=f'{modulo.get_tipo_modulo_display()} - Data Início', initial=modulo.inicio)
            lista.append(f'{modulo.id}_inicio')
            self.fields[f'{modulo.id}_fim'] = forms.DateFieldPlus(label=f'{modulo.get_tipo_modulo_display()} - Data Fim', initial=modulo.fim)
            lista.append(f'{modulo.id}_fim')
        if lista:
            lista.append('controla_tempo')
            self.fieldsets = self.fieldsets + (('Aditivo de Tempo', {'fields': (lista)}),)

        self.instance.aprendizagem = aprendizagem

    def clean(self):
        cleaned_data = super().clean()

        if self.cleaned_data.get('tipos_aditivo'):
            # orientador
            if TipoAditivoAprendizagem.objects.get(pk=TipoAditivoAprendizagem.PROFESSOR_ORIENTADOR) in self.cleaned_data['tipos_aditivo']:
                if not cleaned_data.get('orientador'):
                    self.add_error('orientador', 'Deve ser informado o novo professor orientador.')

            # monitor
            if TipoAditivoAprendizagem.objects.get(pk=TipoAditivoAprendizagem.EMPREGADO_MONITOR) in self.cleaned_data['tipos_aditivo']:
                if not cleaned_data.get('nome_monitor'):
                    self.add_error('nome_monitor', 'Deve ser informado o nome do novo monitor desta aprendizagem.')
                if not cleaned_data.get('telefone_monitor'):
                    self.add_error('telefone_monitor', 'Deve ser informado o telefone do novo monitor desta aprendizagem.')
                if not cleaned_data.get('cargo_monitor'):
                    self.add_error('cargo_monitor', 'Deve ser informado o cargo do novo monitor desta aprendizagem.')
                if not cleaned_data.get('email_monitor'):
                    self.add_error('email_monitor', 'Deve ser informado o e-mail do novo monitor desta aprendizagem.')

            # turno
            if TipoAditivoAprendizagem.objects.get(pk=TipoAditivoAprendizagem.HORARIO) in self.cleaned_data['tipos_aditivo']:
                if not cleaned_data.get('turno'):
                    self.add_error('turno', 'Deve ser informado o novo turno desta aprendizagem.')

            # filial (demanda 562)
            if TipoAditivoAprendizagem.objects.get(pk=TipoAditivoAprendizagem.FILIAL) in self.cleaned_data['tipos_aditivo']:
                if not cleaned_data.get('empresa'):
                    self.add_error('empresa', 'Deve ser informado a nova empresa concedente desta ' 'aprendizagem.')

                if not cleaned_data.get('cidade'):
                    self.add_error('cidade', 'Deve ser informado a cidade da nova empresa concedente desta ' 'aprendizagem.')

                if not cleaned_data.get('logradouro'):
                    self.add_error('logradouro', 'Deve ser informado o logradouro da nova empresa concedente desta ' 'aprendizagem.')

                if not cleaned_data.get('numero'):
                    self.add_error('numero', 'Deve ser informado o número da nova empresa concedente desta ' 'aprendizagem.')

                if not cleaned_data.get('bairro'):
                    self.add_error('bairro', 'Deve ser informado o bairro da nova empresa concedente desta ' 'aprendizagem.')

                if not cleaned_data.get('cep'):
                    self.add_error('cep', 'Deve ser informado o cep da nova empresa concedente desta ' 'aprendizagem.')

        return cleaned_data

    @transaction.atomic
    def save(self, *args, **kwargs):
        # salva o aditivo
        super().save(*args, **kwargs)

        aditivo = self.instance

        # atualiza dados da aprendizagem e seta histórico textual no aditivo recém criado informando
        # a mudança de informações que ocorreu na aprendizagem atualizada
        aprendizagem = aditivo.aprendizagem
        historico = []
        atributos_atualizados = OrderedDict()

        if aditivo.tipos_aditivo.filter(pk=TipoAditivoAprendizagem.PROFESSOR_ORIENTADOR).exists():
            atributos_atualizados['orientador'] = ['orientador']
        if aditivo.tipos_aditivo.filter(pk=TipoAditivoAprendizagem.EMPREGADO_MONITOR).exists():
            atributos_atualizados['monitor'] = ['nome_monitor', 'telefone_monitor', 'cargo_monitor', 'email_monitor', 'observacao']
        if aditivo.tipos_aditivo.filter(pk=TipoAditivoAprendizagem.HORARIO).exists():
            atributos_atualizados['turno'] = ['turno']
        if aditivo.tipos_aditivo.filter(pk=TipoAditivoAprendizagem.FILIAL).exists():
            atributos_atualizados['filial'] = ['empresa', 'cidade', 'logradouro', 'numero', 'complemento', 'bairro', 'cep']

        for grupo in atributos_atualizados.keys():
            historico.append(f'{grupo.capitalize()}:'.upper())
            for atributo in atributos_atualizados[grupo]:
                if hasattr(aprendizagem, atributo):
                    value_anterior = getattr(aprendizagem, atributo)
                    value_atual = self.cleaned_data.get(atributo)

                    if value_atual and value_atual.__class__ in [InMemoryUploadedFile, TemporaryUploadedFile]:
                        value_atual = value_atual.name

                    if atributo == 'orientador':
                        vinculo = value_atual
                        qs = Professor.objects.filter(vinculo__id=vinculo.pk)
                        if qs.exists():
                            professor = qs[0]
                        else:
                            professor = Professor()
                            professor.vinculo = vinculo
                            professor.save()
                            Group.objects.get(name='Professor').user_set.add(professor.vinculo.user)
                        value_atual = professor

                    setattr(aprendizagem, atributo, value_atual)

                    # ajustes dos valores para setar o histórico
                    if value_anterior.__class__ == FieldFile:
                        value_anterior = value_anterior.name

                    if value_anterior in [True, False]:
                        value_anterior = 'Sim' if value_anterior else 'Não'

                    if value_atual in [True, False]:
                        value_atual = 'Sim' if value_atual else 'Não'

                    if value_anterior.__class__ == Professor:
                        value_anterior = value_anterior.vinculo

                    if value_atual.__class__ == Professor:
                        value_atual = value_atual.vinculo

                    if value_anterior.__class__ == PessoaJuridica:
                        value_anterior = f'{value_anterior}'

                    if value_atual.__class__ == PessoaJuridica:
                        value_atual = f'{value_atual}'

                    label_field = aprendizagem._meta.get_field(atributo).verbose_name
                    historico.append(f'{label_field}: {format_(value_anterior)} → {format_(value_atual)}')
            historico.append('')
        historico_tempo = []
        if aditivo.tipos_aditivo.filter(pk=TipoAditivoAprendizagem.TEMPO).exists():
            for modulo in ModuloAprendizagem.objects.filter(aprendizagem=aprendizagem):
                campo_inicio = self.cleaned_data.get(f'{modulo.id}_inicio')
                campo_fim = self.cleaned_data.get(f'{modulo.id}_fim')
                alterou = False
                if campo_inicio != modulo.inicio:
                    if not bool(historico_tempo):
                        historico_tempo.append('TEMPO:')
                    historico_tempo.append(f'Data Início - {modulo.get_tipo_modulo_display()}: {format_(modulo.inicio)} → {format_(campo_inicio)}')
                    modulo.inicio = campo_inicio
                    alterou = True
                if campo_fim != modulo.fim:
                    if not bool(historico_tempo):
                        historico_tempo.append('TEMPO:')
                    historico_tempo.append(f'Data Fim - {modulo.get_tipo_modulo_display()}: {format_(modulo.fim)} → {format_(campo_fim)}')
                    modulo.fim = campo_fim
                    alterou = True
                if alterou:
                    modulo.save()
        if bool(historico_tempo):
            for registro in historico_tempo:
                historico.append(registro)
        aprendizagem.save()
        aditivo.historico = '\n'.join(historico)
        aditivo.save()

        # notifica por email
        if aditivo.tipos_aditivo.filter(pk=TipoAditivoAprendizagem.PROFESSOR_ORIENTADOR).exists():
            aprendizagem.enviar_email_orientador_recem_cadastrado()

        if aditivo.tipos_aditivo.filter(pk=TipoAditivoAprendizagem.EMPREGADO_MONITOR).exists():
            aprendizagem.enviar_email_empregado_monitor_recem_cadastrado()


class RelatorioModuloAprendizagemForm(forms.ModelFormPlus):
    class Meta:
        model = RelatorioModuloAprendizagem
        exclude = ('aprendizagem', 'eh_relatorio_do_empregado_monitor', 'ultimo_editor', 'modulo_aprendizagem')

    fieldsets = (('Atividades Previstas', {'fields': ('avaliacao_atividades', 'comentarios_atividades')}), ('Atividades Não Previstas', {'fields': ('outras_atividades',)}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.eh_relatorio_do_empregado_monitor:
            self.fieldsets += (('Relação Teoria/Prática', {'fields': ('aprendizagem_na_area_formacao', 'aprendizagem_contribuiu', 'aplicou_conhecimento')}),)
            self.fieldsets += (('Avaliação da Experiência como Aprendiz', {'fields': ('avaliacao_conceito',)}),)
            del self.fields['nota_aprendiz']
            del self.fields['avaliacao_comentarios']
            self.fields['relatorio'].help_text = 'O relatório do módulo deve estar assinado pelo Aprendiz, Orientador e pelo Empregado Monitor.'
        if self.instance.eh_relatorio_do_empregado_monitor:
            self.fieldsets += (('Avaliação do Desempenho do Aprendiz', {'fields': ('nota_aprendiz',)}),)
            self.fieldsets += (('Comentários e Sugestões', {'fields': ('avaliacao_comentarios',)}),)
            del self.fields['aprendizagem_na_area_formacao']
            del self.fields['aprendizagem_contribuiu']
            del self.fields['aplicou_conhecimento']
            del self.fields['avaliacao_conceito']
        self.fieldsets += (('Data do Relatório', {'fields': ('data_relatorio',)}),)
        self.fieldsets += (('Relatório', {'fields': ('relatorio',)}),)


class EncerrarAprendizagemForm(forms.ModelFormPlus):
    class Meta:
        model = Aprendizagem
        fields = ('data_encerramento', 'encerramento_por', 'motivo_encerramento', 'motivacao_rescisao', 'ch_final', 'laudo_avaliacao', 'comprovante_encerramento')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ch_final'].help_text = self.instance.get_sugestao_ch_final()

    fieldsets = (
        ('Dados do Encerramento', {'fields': ('encerramento_por', 'motivo_encerramento', 'motivacao_rescisao', 'data_encerramento', 'ch_final')}),
        ('Documentação', {'fields': ('comprovante_encerramento', 'laudo_avaliacao')}),
    )

    def clean(self):
        cleaned_data = super().clean()
        data_encerramento = cleaned_data.get('data_encerramento', None)
        if data_encerramento:
            if cleaned_data.get('encerramento_por') and cleaned_data['encerramento_por'] == Aprendizagem.CONCLUSAO:
                if data_encerramento != self.instance.get_data_prevista_encerramento():
                    raise forms.ValidationError(
                        'No encerramento por conclusão, a data de encerramento deve ser a data prevista para o fim, que é a data de encerramento do último módulo.'
                    )
                if self.instance.ha_pendencia_relatorio_aprendiz(data_encerramento):
                    raise forms.ValidationError('Não é possível encerrar a aprendizagem, pois o aprendiz não cadastrou todos os relatórios.')
                if self.instance.ha_pendencia_relatorio_monitor(data_encerramento):
                    raise forms.ValidationError('Não é possível encerrar a aprendizagem, pois o monitor não realizou todas as avaliações do estágio.')
            if cleaned_data.get('encerramento_por') and cleaned_data['encerramento_por'] == Aprendizagem.RESCISAO:
                if (
                    not cleaned_data['laudo_avaliacao']
                    and cleaned_data.get('motivo_encerramento')
                    and cleaned_data['motivo_encerramento'] == Aprendizagem.MOTIVO_DESEMPENHO_INSUFICIENTE_INADAPTACAO
                ):
                    self._errors['laudo_avaliacao'] = self.error_class(
                        ['Na rescisão por desempenho insuficiente ou inadaptação do aprendiz é necessário anexar o Laudo de Avaliação.']
                    )
                    del self.cleaned_data['laudo_avaliacao']
                if self.instance.ha_pendencia_relatorio_aprendiz(data_encerramento):
                    raise forms.ValidationError('Não é possível encerrar a aprendizagem, pois o aprendiz não cadastrou seus relatórios pendentes.')
                if self.instance.ha_pendencia_relatorio_monitor(data_encerramento):
                    raise forms.ValidationError('Não é possível encerrar a aprendizagem, pois o monitor não cadastrou seus relatórios pendentes.')
        return cleaned_data


class EncerrarAprendizagemAbandonoMatriculaIrregularForm(forms.ModelFormPlus):
    class Meta:
        model = Aprendizagem
        fields = ('data_encerramento', 'encerramento_por', 'motivo_encerramento', 'motivacao_rescisao', 'ch_final', 'desvinculado_matricula_irregular')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ch_final'].help_text = self.instance.get_sugestao_ch_final()
        self.fields['desvinculado_matricula_irregular'].required = True
        self.fields['motivacao_rescisao'].required = True

    fieldsets = (
        ('Dados do Encerramento', {'fields': ('encerramento_por', 'motivo_encerramento', 'motivacao_rescisao', 'data_encerramento', 'ch_final')}),
        ('Finalizar sem requisitos por abandono do aluno/matrícula irregular', {'fields': ('desvinculado_matricula_irregular',)}),
    )

    def clean(self):
        cleaned_data = super().clean()
        desvinculado_matricula_irregular = cleaned_data.get('desvinculado_matricula_irregular', None)
        if not desvinculado_matricula_irregular:
            self._errors['desvinculado_matricula_irregular'] = self.error_class(['Necessária confirmação.'])
        return cleaned_data


class EncerrarAtividadeProfissionalEfetivaForm(forms.ModelFormPlus):
    class Meta:
        model = AtividadeProfissionalEfetiva
        fields = ('encerramento', 'ch_final', 'observacoes')

    fieldsets = (('Dados do Encerramento', {'fields': ('encerramento', 'ch_final', 'observacoes')}),)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ch_final'].help_text = self.instance.get_sugestao_ch_final()

    def clean(self):
        cleaned_data = super().clean()
        if not self.instance.relatorio_final_aluno:
            raise forms.ValidationError(
                'Só é possível encerrar normalmente uma atividade profissional efetiva se a ' 'Declaração de Realização de Atividade Profissional Efetiva já estiver cadastrada.'
            )
        return cleaned_data

    def save(self, *args, **kwargs):
        self.instance.situacao = AtividadeProfissionalEfetiva.CONCLUIDA
        return super().save(*args, **kwargs)


class CadastrarCancelamentoAtividadeProfissionalEfetivaForm(forms.ModelFormPlus):
    class Meta:
        model = AtividadeProfissionalEfetiva
        fields = ('cancelamento', 'motivo_cancelamento', 'descricao_cancelamento')

    fieldsets = (('Dados do Encerramento', {'fields': ('cancelamento', 'motivo_cancelamento', 'descricao_cancelamento')}),)

    def save(self, *args, **kwargs):
        self.instance.situacao = AtividadeProfissionalEfetiva.NAO_CONCLUIDA
        return super().save(*args, **kwargs)


class SolicitacaoCancelamentoEncerramentoEstagioForm(forms.ModelFormPlus):
    class Meta:
        model = SolicitacaoCancelamentoEncerramentoEstagio
        fields = ('justificativa',)


class SolicitacaoCancelamentoEncerramentoAprendizagemForm(forms.ModelFormPlus):
    class Meta:
        model = SolicitacaoCancelamentoEncerramentoEstagio
        fields = ('justificativa',)


class SolicitacaoCancelamentoEncerramentoAtividadeProfissionalEfetivaForm(forms.ModelFormPlus):
    class Meta:
        model = SolicitacaoCancelamentoEncerramentoEstagio
        fields = ('justificativa',)


class RelatorioAtividadeProfissionalEfetivaForm(forms.ModelFormPlus):
    class Meta:
        model = AtividadeProfissionalEfetiva
        fields = (
            'avaliacao_atividades',
            'comentarios_atividades',
            'outras_atividades',
            'area_formacao',
            'contribuiu',
            'aplicou_conhecimento',
            'avaliacao_conceito',
            'data_relatorio',
            'relatorio_final_aluno',
        )

    fieldsets = (
        ('Atividades Previstas', {'fields': ('avaliacao_atividades', 'comentarios_atividades')}),
        ('Atividades Não Previstas', {'fields': ('outras_atividades',)}),
        ('Relação Teoria/Prática', {'fields': ('area_formacao', 'contribuiu', 'aplicou_conhecimento')}),
        ('Avaliação do Estágio', {'fields': ('avaliacao_conceito',)}),
        ('Relatório', {'fields': ('data_relatorio', 'relatorio_final_aluno')}),
    )

    def save(self, *args, **kwargs):
        self.instance.notificar_orientador_envio_relatorio_final_aluno(self.request.user)
        return super().save(*args, **kwargs)


class AtividadeProfissionalEfetivaForm(forms.ModelFormPlus):

    SITUACOES = [('', '---------'), ('em_andamento', 'Em Andamento'), ('concluida', 'Concluída')]

    situacao_atividade = forms.ChoiceField(label='Situação da Atividade', choices=SITUACOES)
    vinculo = forms.ModelChoiceFieldPlus(queryset=Vinculo.objects.servidores(), widget=AutocompleteWidget(search_fields=Vinculo.SEARCH_FIELDS), label='Orientador', required=True)

    class Meta:
        model = AtividadeProfissionalEfetiva
        exclude = ('orientador',)

    class Media:
        js = ('/static/estagios/js/AtividadeProfissionalEfetivaForm.js',)

    fieldsets = (
        ('Dados Gerais', {'fields': ('aluno', 'instituicao', 'razao_social', 'vinculo', 'tipo', 'descricao_outro_tipo', 'situacao_atividade')}),
        ('Período e Carga Horária', {'fields': ('inicio', 'data_prevista_encerramento', 'ch_semanal')}),
        ('Documentação', {'fields': ('documentacao_comprobatoria', 'plano_ atividades')}),
        ('Relação das Atividades', {'fields': ('atividades',)}),
        ('Encerramento', {'fields': ('anterior_20171', 'encerramento', 'ch_final', 'relatorio_final_aluno', 'observacoes')}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['aluno'].widget = AutocompleteWidget(search_fields=Aluno.SEARCH_FIELDS)
        self.fields['aluno'].queryset = self.fields['aluno'].queryset.filter(matriz__isnull=False)
        self.fields['ch_semanal'].widget = forms.IntegerWidget()
        if self.instance.pk:
            del self.fields['situacao_atividade']

        if self.instance.pk and self.instance.orientador:
            try:
                vinculo = self.instance.orientador.vinculo
                self.fields['vinculo'].initial = vinculo
            except Exception:
                pass

        if 'encerramento' in self.fields:
            self.fields['encerramento'].required = False
            self.fields['ch_final'].required = False
            self.fields['relatorio_final_aluno'].required = False

    def clean(self):
        cleaned_data = super().clean()
        if not bool(self.errors) and not self.instance.pk:
            if cleaned_data['situacao_atividade'] == 'concluida':
                if not cleaned_data['encerramento']:
                    self._errors['encerramento'] = self.error_class(['É necessário preencher a data do encerramento numa Atividade Profissional Efetiva já concluída.'])
                    del self.cleaned_data['encerramento']
                if not cleaned_data['ch_final']:
                    self._errors['ch_final'] = self.error_class(['É necessário preencher a C.H. cumprida numa Atividade Profissional Efetiva já concluída.'])
                    del self.cleaned_data['ch_final']
                if not cleaned_data['relatorio_final_aluno'] and not cleaned_data['anterior_20171']:
                    self._errors['relatorio_final_aluno'] = self.error_class(
                        ['É necessário preencher o relatório final do aluno numa Atividade Profissional Efetiva já concluída.']
                    )
                    del self.cleaned_data['relatorio_final_aluno']

        return cleaned_data

    @transaction.atomic
    def save(self, *args, **kwargs):
        vinculo = self.cleaned_data['vinculo']
        qs = Professor.objects.filter(vinculo__id=vinculo.pk)
        if qs.exists():
            self.instance.orientador = qs[0]
        else:
            professor = Professor()
            professor.vinculo = vinculo
            professor.save()
            self.instance.orientador = professor
            Group.objects.get(name='Professor').user_set.add(professor.vinculo.user)

        if self.cleaned_data.get('situacao_atividade', None) == 'concluida':
            self.instance.situacao = AtividadeProfissionalEfetiva.CONCLUIDA
        else:
            self.instance.situacao = AtividadeProfissionalEfetiva.EM_ANDAMENTO

        notificar = not self.instance.pk
        retorno = super().save(*args, **kwargs)
        if notificar:
            self.instance.notificar_aluno_inicialmente()
            self.instance.orientador_recem_cadastrado()
        return retorno


class JustificativaVisitaEstagioForm(forms.ModelFormPlus):
    class Meta:
        model = JustificativaVisitaEstagio
        exclude = ('pratica_profissional', 'inicio', 'fim')

    fieldsets = (
        ('Justificativa', {'fields': ('motivos',)}),
        ('Outros Acompanhamentos', {'fields': ('outros_acompanhamentos',)}),
        ('Documentação', {'fields': ('formulario_justificativa',)}),
    )


class JustificativaVisitaModuloAprendizagemForm(forms.ModelFormPlus):
    class Meta:
        model = JustificativaVisitaModuloAprendizagem
        exclude = ('modulo',)

    fieldsets = (
        ('Justificativa', {'fields': ('motivos',)}),
        ('Outros Acompanhamentos', {'fields': ('outros_acompanhamentos',)}),
        ('Documentação', {'fields': ('formulario_justificativa',)}),
    )
