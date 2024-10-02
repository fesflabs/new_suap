# -*- coding: utf-8 -*-
import datetime

from django.contrib.auth import authenticate
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from catalogo_provedor_servico.models import Solicitacao, Servico, ServicoEquipe, ServicoGerenteEquipeLocal
from comum.models import Ano, Vinculo
from djtools import forms
from djtools.forms.widgets import TreeWidget, AutocompleteWidget
from documento_eletronico.models import TipoDocumento, Documento
from edu.forms import EfetuarMatriculaForm
from edu.models import Aluno, Turno, Polo, FormaIngresso, Convenio, MatrizCurso, LinhaPesquisa
from processo_eletronico.forms import FinalizarRequerimentoForm
from processo_seletivo.models import CandidatoVaga
from rh.models import Setor, UnidadeOrganizacional, Papel


class ConfiguracaoForm(forms.FormPlus):
    # url = forms.CharFieldPlus(label='URL do gitlab', required=False)
    # gitlab_token = forms.CharFieldPlus(label='Token do gitlab', required=False)
    # gitlab_suap_id = forms.CharFieldPlus(label='ID do projeto SUAP', required=False)

    # api de serviços públicos digitais
    url_servicos_gov_br = forms.URLField(label='URL Serviços GOV.BR', required=False)

    # api de informações dos orgãos
    url_orgaos_gov_br = forms.URLField(label='URL Órgãos GOV.BR', required=False)

    # api de acompanhamentos
    url_acompanhamentos_gov_br = forms.URLField(label='Acompanhamento GOV.BR - URL', required=False)
    user_acompanhamentos_gov_br = forms.EmailField(label='Acompanhamento GOV.BR - User', required=False)
    password_acompanhamentos_gov_br = forms.CharFieldPlus(label='Acompanhamento GOV.BR - Password', required=False)

    # api de avaliação de serviços públicos
    url_avaliacao_gov_br = forms.URLField(label='Avaliação GOV.BR - URL', required=False)
    user_avaliacao_gov_br = forms.EmailField(label='Avaliação GOV.BR - User', required=False)
    password_avaliacao_gov_br = forms.CharFieldPlus(label='Avaliação GOV.BR - Password', required=False)

    url_catalogo_digital = forms.URLField(label='URL do Catálogo Digital', required=False)
    enviar_acompanhamentos_govbr = forms.BooleanField(label='Enviar Acompanhamento GOV.BR', required=False)
    request_timeout_gov_br = forms.IntegerField(label='Request Timeout Para Consumir APIs GOV.BR (segundos)',
                                                required=False)
    orgao_id_portal_servicos_govbr = forms.IntegerField(label='ID do Órgão no Serviços GOV.BR', required=False)

    # Api de envio de sms
    url_api_sms = forms.URLField(label='URL da API de Envio de SMS', required=False)
    username_api_sms = forms.CharFieldPlus(label='Username da API de Envio de SMS', required=False)
    token_api_sms = forms.CharFieldPlus(label='Token da API de Envio de SMS', required=False)

    # API Plataforma Notifica Gov.BR
    api_key_notifica_govbr = forms.CharFieldPlus(label='API Key da Plataforma Notifica', required=False)
    id_template_notifica_padrao_suap_sms = forms.CharFieldPlus(label='ID Template padrão SMS na Plataforma Notifica',
                                                               required=False)
    id_template_notifica_padrao_suap_email = forms.CharFieldPlus(
        label='ID Template padrão Email na Plataforma Notifica', required=False)
    id_template_notifica_padrao_suap_app_govbr = forms.CharFieldPlus(
        label='ID Template padrão App Gov.BR na Plataforma Notifica', required=False)
    habilitar_notifica_govbr = forms.BooleanField(label='Habilitar Serviço do GovBR', required=False)


# Formulário usado somente em ambiente de desenvolvimento (DEBUG = TRUE)
class ApagarAtendimentoForm(forms.FormPlus):
    SUBMIT_LABEL = 'Apagar'
    solicitacao = forms.ModelChoiceFieldPlus(Solicitacao.objects.all(), label='Solicitação', required=True)


class GerenciarEquipeForm(forms.FormPlus):
    SUBMIT_LABEL = 'Salvar'
    solicitacao = forms.ModelChoiceFieldPlus(Solicitacao.objects.all(), label='Solicitação', required=True)

    class Meta:
        model = ServicoGerenteEquipeLocal
        fields = ()


class CatalogoEfetuarMatriculaForm(EfetuarMatriculaForm):
    declaracao_etnia = forms.BooleanField(label='Declaração de Etnia', required=True)
    declaracao_didatica = forms.BooleanField(label='Declaração Didática', required=True)
    declaracao_legais = forms.BooleanField(label='Declaração Legal', required=True)
    declaracao_veracidade = forms.BooleanField(label='Declaração de Veracidade', required=True)
    declaracao_conclusao = forms.BooleanField(label='Declaração de Conclusão', required=True)


class SolicitacaoMatriculaForm(forms.FormPlus):
    cpf = forms.BrCpfField(required=False, widget=forms.TextInput(attrs={'readonly': 'True'}))
    nome = forms.CharFieldPlus(required=True, label='Nome', width=500,
                               widget=forms.TextInput(attrs={'readonly': 'True'}))

    # dados da matrícula
    ano_letivo = forms.ModelChoiceField(Ano.objects.ultimos(), required=True, label='Ano Letivo')
    periodo_letivo = forms.ChoiceField(required=True, label='Período Letivo', choices=Aluno.PERIODO_LETIVO_CHOICES)
    turno = forms.ModelChoiceField(Turno.objects, required=True, label='Turno')
    polo = forms.ModelChoiceField(Polo.objects, required=False, label='Polo EAD', help_text='Apenas para o Turno EAD.')
    forma_ingresso = forms.ModelChoiceField(FormaIngresso.objects, required=True, label='Forma de Ingresso')
    cota_sistec = forms.ChoiceField(label='Cota SISTEC', choices=Aluno.COTA_SISTEC_CHOICES, required=False,
                                    widget=forms.HiddenInput())
    cota_mec = forms.ChoiceField(label='Cota MEC', choices=Aluno.COTA_MEC_CHOICES, required=False,
                                 widget=forms.HiddenInput())
    possui_convenio = forms.BooleanRequiredField(label='Possui Convênio')
    convenio = forms.ModelChoiceField(Convenio.objects, required=False, label='Convênio')
    data_conclusao_intercambio = forms.DateFieldPlus(
        required=False, label='Conclusão do Intercâmbio',
        help_text='Preencha esse campo com a data de conclusão do intercâmbio caso se trate de um aluno de intercâmbio'
    )
    matriz_curso = forms.ModelChoiceFieldPlus(MatrizCurso.objects, required=True, label='Matriz/Curso')
    linha_pesquisa = forms.ModelChoiceFieldPlus(
        LinhaPesquisa.objects, required=False, label='Linha de Pesquisa',
        help_text='Obrigatório para alunos de Mestrado e Doutourado. Caso não saiba, escreva "A definir".'
    )
    aluno_especial = forms.BooleanField(required=False, label='Aluno Especial?',
                                        help_text='Marque essa opção caso se trate de um aluno especial em curso de Pós-Graduação')
    numero_pasta = forms.CharFieldPlus(label='Número da Pasta', required=False, max_length=255)

    observacao_matricula = forms.CharField(widget=forms.Textarea(), required=False, label='Observação')

    def __init__(self, *args, **kwargs):
        self.candidato_vaga = kwargs.pop('candidato_vaga')
        super(SolicitacaoMatriculaForm, self).__init__(*args, **kwargs)
        if self.candidato_vaga:
            if 'forma_ingresso' in self.initial:
                self.fields['forma_ingresso'].queryset = FormaIngresso.objects.filter(
                    pk=self.candidato_vaga.oferta_vaga.lista.forma_ingresso_id)
                self.fields['forma_ingresso'].initial = self.candidato_vaga.oferta_vaga.lista.forma_ingresso_id
            else:
                self.fields['forma_ingresso'].queryset = FormaIngresso.objects.none()

            if 'matriz_curso' in self.initial:
                self.fields['matriz_curso'].queryset = MatrizCurso.locals.filter(matriz__ativo=True)
                if self.candidato_vaga:
                    self.fields['matriz_curso'].queryset = self.fields['matriz_curso'].queryset.filter(
                        curso_campus=self.candidato_vaga.oferta_vaga.oferta_vaga_curso.curso_campus)

            if self.candidato_vaga.oferta_vaga.oferta_vaga_curso.campus_polo:
                self.fields[
                    'polo'].help_text = f'Apenas para o Turno EAD. O candidato escolheu o polo {self.candidato_vaga.oferta_vaga.oferta_vaga_curso.campus_polo}'

            # if 'cpf' in self.cleaned_data:
            #     qs = PessoaFisica.objects.filter(cpf=self.cleaned_data['cpf'])
            #     if qs:
            #         pessoa_fisica = qs[0]
            #         self.initial.update(nome=pessoa_fisica.nome, sexo=pessoa_fisica.sexo, data_nascimento=pessoa_fisica.nascimento_data)
            # if 'pais_origem' in self.fields:
            #     self.fields['pais_origem'].queryset = Pais.objects.all().exclude(nome='Brasil')

    # def clean_ano_letivo(self):
    #     ano_letivo = self.cleaned_data.get('ano_letivo')
    #     if ano_letivo and self.candidato_vaga:
    #         if ano_letivo != self.candidato_vaga.candidato.edital.ano:
    #             raise forms.ValidationError('Ano incompatível com o do edital do candidato, que é {}'.format(self.candidato_vaga.candidato.edital.ano))
    #     return ano_letivo
    #
    # def clean_periodo_letivo(self):
    #     periodo_letivo = self.cleaned_data.get('periodo_letivo')
    #     if periodo_letivo and self.candidato_vaga:
    #         if int(periodo_letivo) != self.candidato_vaga.candidato.edital.semestre:
    #             raise forms.ValidationError('Período incompatível com o do edital do candidato, que é {}'.format(self.candidato_vaga.candidato.edital.semestre))
    #     return periodo_letivo
    #
    # def clean_polo(self):
    #     matriz_curso = self.cleaned_data('matriz_curso')
    #     polo = self.cleaned_data('polo')
    #
    #     if matriz_curso:
    #         if polo:
    #             if not matriz_curso.curso_campus.diretoria.ead:
    #                 raise forms.ValidationError('O campo Polo deve ser definido apenas para cursos EAD.')
    #         elif matriz_curso.curso_campus.diretoria.ead:
    #             raise ValidationError('É necessário informar o Polo do aluno.')
    #
    #     return self.cleaned_data.get('polo')
    #
    # def clean_linha_pesquisa(self):
    #     if 'matriz_curso' in self.data and self.data['matriz_curso']:
    #         qs_matriz_curso = MatrizCurso.objects.filter(pk=self.data['matriz_curso'])
    #         if qs_matriz_curso:
    #             matriz_curso = qs_matriz_curso[0]
    #             if (matriz_curso.curso_campus.modalidade.pk in [Modalidade.MESTRADO, Modalidade.DOUTORADO]) and not self.cleaned_data['linha_pesquisa']:
    #                 raise forms.ValidationError('Este campo é obrigatório por se tratar de um aluno de um curso de  {}.'.format(matriz_curso.curso_campus.modalidade))
    #     return 'linha_pesquisa' in self.cleaned_data and self.cleaned_data['linha_pesquisa'] or None
    #
    # def clean_matriz_curso(self):
    #     matriz_curso = self.cleaned_data.get('matriz_curso')
    #     if matriz_curso:
    #         if self.candidato_vaga and not matriz_curso.curso_campus == self.candidato_vaga.oferta_vaga.oferta_vaga_curso.curso_campus:
    #             raise forms.ValidationError('Esta matriz não é válida.')
    #     return matriz_curso
    #
    # def clean_convenio(self):
    #     possui_convenio = self.cleaned_data.get('possui_convenio')
    #     if possui_convenio and not self.data.get('convenio'):
    #         raise forms.ValidationError('Informe o convênio')
    #     elif not possui_convenio and self.data.get('convenio'):
    #         raise forms.ValidationError('Não é possível selecionar um convênio quando o valor do campo "Possui Convênio?" é "Não".')
    #     return self.cleaned_data.get('convenio')


class EmissaoDiplomaForm(FinalizarRequerimentoForm):
    pass


class IndeferirSolicitacaoForm(forms.ModelFormPlus):
    detalhamento = forms.CharFieldPlus(max_length=1000, required=True, label='Detalhamento de Status', widget=forms.Textarea())

    class Meta:
        model = Solicitacao
        fields = ()

    def save(self, *args, **kwargs):
        detalhamento = self.cleaned_data['detalhamento']
        self.instance.status_detalhamento = detalhamento
        self.instance.status = Solicitacao.STATUS_NAO_ATENDIDO
        super().save(*args, **kwargs)

        etapa = self.instance.solicitacaoetapa_set.get(numero_etapa=1).get_dados_as_json()
        candidato_vaga = None

        for dado in etapa['formulario']:
            if dado['name'] == 'candidato_vaga':
                candidato_vaga = CandidatoVaga.objects.get(pk=dado['value'])
                break

        if candidato_vaga:
            candidato_vaga.registrar_inaptidao()


class RetornarParaAnaliseSolicitacaoForm(forms.ModelFormPlus):
    detalhamento = forms.CharFieldPlus(required=True, label='Detalhamento de Status', widget=forms.Textarea())

    class Meta:
        model = Solicitacao
        fields = ()

    def save(self, *args, **kwargs):
        detalhamento = self.cleaned_data['detalhamento']
        self.instance.status_detalhamento = detalhamento
        self.instance.status = Solicitacao.STATUS_EM_ANALISE
        super().save(*args, **kwargs)

        etapa = self.instance.solicitacaoetapa_set.get(numero_etapa=1).get_dados_as_json()
        candidato_vaga = None

        for dado in etapa['formulario']:
            if dado['name'] == 'candidato_vaga':
                candidato_vaga = CandidatoVaga.objects.get(pk=dado['value'])
                break
        if candidato_vaga:
            candidato_vaga.retornar_para_apto()


class DashboradFiltroForm(forms.FormPlus):
    METHOD = 'GET'

    servico = forms.ModelChoiceFieldPlus(label='Serviço', queryset=Servico.objects)
    uo = forms.ModelChoiceFieldPlus(label='Unidade Organizacional', queryset=UnidadeOrganizacional.objects.uo(),
                                    required=False)
    data_inicio = forms.DateFieldPlus(label='Data Inicial')
    data_fim = forms.DateFieldPlus(label='Data Final')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hoje = datetime.date.today()
        self.fields['data_inicio'].initial = hoje
        self.fields['data_fim'].initial = hoje


# TODO: Ver se é viável unir esse form com AtribuirAtendimentoForm. Eles tem a mesma ideia, só que o primeiro é voltado
# para o procedimento em lote e o outro o procediumento normal em cima de uma solicitação.
class AtribuirAvaliadorForm(forms.FormPlus):
    action = forms.CharField(widget=forms.MultipleHiddenInput)
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    avaliador = forms.ModelChoiceFieldPlus(label='Avaliador', queryset=Vinculo.objects)
    instrucao = forms.CharFieldPlus(label='Instrução', max_length=1000, required=False)

    def __init__(self, *args, **kwargs):
        queryset = kwargs.pop('queryset')
        super().__init__(*args, **kwargs)
        servicos = Servico.objects.filter(pk__in=queryset.values('servico').distinct())

        # Rotina antiga feita por Gugu.
        # pessoas_fisica = PessoaFisica.objects.filter(
        #     pk__in=ServicoEquipe.objects.filter(servico__in=servicos).values('pessoa_fisica').distinct()
        #
        # )
        # self.fields['avaliador'].queryset = pessoas_fisica

        # Rotina nova feita por Misael.
        # Buscando as pessoas que podem assumir a solicitação em questão. Obs: Tive que usar essa estratégia de montar
        # uma lista de IDs de pessoas físicas uma vez que não é possível de ser feito um filtro por UO na entidade PessoaFisica.
        servico_equipe_ids = ServicoEquipe.objects.filter(servico__in=servicos,
                                                          campus=self.request.user.get_vinculo().setor.uo).values_list(
            'vinculo_id', flat=True)
        vinculos_habilitados = Vinculo.objects.filter(id__in=servico_equipe_ids)
        self.fields['avaliador'].queryset = vinculos_habilitados


# TODO: Rever nomes. Se a atividade é de Avaliacao de Solicitação, o nome mais apropriado é
# definir as classes usando a palavra Avaliador ou Avaliacao. ServicoEquipe, Atendimento, fica meio confuso.
class AtribuirAtendimentoForm(forms.ModelFormPlus):
    # responsavel = forms.ModelChoiceFieldPlus(label='Avaliador', queryset=PessoaFisica.objects, required=True)
    # instrucao = forms.CharFieldPlus(label='Instrução', max_length=100, required=True, initial=None)

    class Meta:
        model = Solicitacao
        fields = ('vinculo_responsavel', 'instrucao',)

    def __init__(self, *args, **kwargs):
        super(AtribuirAtendimentoForm, self).__init__(*args, **kwargs)
        self.initial['vinculo_responsavel'] = None
        self.initial['instrucao'] = None

        # Buscando as pessoas que podem assumir a solicitação em questão. Obs: Tive que usar essa estratégia de montar
        # uma lista de IDs de pessoas físicas uma vez que não é possível de ser feito um filtro por UO na entidade PessoaFisica.
        servico_equipe_ids = ServicoEquipe.objects.filter(servico=self.instance.servico,
                                                          campus=self.instance.uo).values_list('vinculo_id',
                                                                                               flat=True)
        vinculos_habilitados = Vinculo.objects.filter(id__in=servico_equipe_ids)
        if self.instance.vinculo_responsavel:
            vinculos_habilitados = vinculos_habilitados.exclude(id=self.instance.vinculo_responsavel.id)
        self.fields['vinculo_responsavel'].queryset = vinculos_habilitados

    def _atribuir_responsavel(self):
        vinculo_atribuinte = self.request.user.get_vinculo()
        vinculo_responsavel = self.cleaned_data.get('vinculo_responsavel')
        self.instance.atribuir_responsavel(vinculo_atribuinte=vinculo_atribuinte,
                                           vinculo_responsavel=vinculo_responsavel,
                                           data_associacao_responsavel=datetime.datetime.now(),
                                           instrucao=self.cleaned_data.get('instrucao'))

    def clean(self):
        self._atribuir_responsavel()
        return super().clean()

    def save(self, *args, **kwargs):
        self._atribuir_responsavel()
        super().save(*args, **kwargs)


class PeticaoEletronicaForm(forms.FormPlus):
    senha = forms.CharField(widget=forms.PasswordInput)
    papel = forms.ModelChoiceField(label='Perfil', queryset=Papel.objects.none())

    # Dados para encaminhar para setor
    tipo_busca_setor = forms.ChoiceField(widget=forms.RadioSelect(), required=True, label="Destino do primeiro trâmite")
    destinatario_setor_autocompletar = forms.ModelChoiceField(label="Setor de Destino", queryset=Setor.objects,
                                                              required=False, widget=AutocompleteWidget())
    destinatario_setor_arvore = forms.ModelChoiceField(label="Setor de Destino", queryset=Setor.objects, required=False,
                                                       widget=TreeWidget())

    def is_tipo_busca_setor_arvore(self):
        return self.cleaned_data.get('tipo_busca_setor') == 'arvore'

    def is_tipo_busca_setor_autocompletar(self):
        return self.cleaned_data.get('tipo_busca_setor') == 'autocompletar'

    def get_destino(self):
        if self.is_tipo_busca_setor_autocompletar():
            return self.cleaned_data.get('destinatario_setor_autocompletar', None)
        if self.is_tipo_busca_setor_arvore():
            return self.cleaned_data.get('destinatario_setor_arvore', None)

    def __init__(self, *args, **kwargs):
        anexos = kwargs.pop('anexos')
        campus_id = kwargs.pop('campus_id')
        campus = UnidadeOrganizacional.objects.get(id=campus_id)

        super(PeticaoEletronicaForm, self).__init__(*args, **kwargs)

        self.fields['papel'].queryset = self.request.user.get_relacionamento().papeis_ativos

        TIPO_BUSCA_SETOR_CHOICE = (
            ('autocompletar', 'Buscar usando o Autocompletar'), ('arvore', 'Buscar usando a Árvore'))
        self.fields['tipo_busca_setor'].choices = TIPO_BUSCA_SETOR_CHOICE
        self.fields['destinatario_setor_autocompletar'].label = f'Setor de Destino (Campus {campus})'
        self.fields['destinatario_setor_autocompletar'].queryset = Setor.objects.filter(uo__id=campus_id)
        self.fields['destinatario_setor_arvore'].label = f'Setor de Destino (Campus {campus})'
        self.fields['destinatario_setor_arvore'].queryset = Setor.objects.filter(uo__id=campus_id)

        self.fieldsets = tuple()
        count = 1
        for anexo in anexos:
            self.fields[anexo['name']] = forms.CharFieldPlus(label='Descrição', max_length=510,
                                                             initial=anexo['descricao'])
            self.fields[anexo['name']].widget.attrs['readonly'] = True
            self.fields[anexo['name'] + '_tipo'] = forms.ModelChoiceField(TipoDocumento.ativos,
                                                                          label='Tipo do Documento', required=True)
            self.fields[anexo['name'] + '_nivel_acesso'] = forms.ChoiceField(choices=((None, '---------'), (Documento.NIVEL_ACESSO_RESTRITO, 'Restrito'), (Documento.NIVEL_ACESSO_PUBLICO, 'Público')),
                                                                             label='Nível de Acesso', required=True)
            self.fieldsets += ((f'Documento {count}', {'fields': (anexo['name'], anexo['name'] + '_tipo', anexo['name'] + '_nivel_acesso',)}),)
            count += 1

        self.fieldsets += (('Setor de Destino', {
            'fields': ('tipo_busca_setor', 'destinatario_setor_autocompletar', 'destinatario_setor_arvore',)}),)
        self.fieldsets += (('Assinatura', {'fields': ('papel', 'senha',)}),)

    class Media:
        js = ('/static/processo_eletronico/js/RequerimentoFormCadastrar.js',)

    def clean_papel(self):
        papel = self.cleaned_data.get('papel', None)

        relacionamento = self.request.user.get_relacionamento()

        if not papel or papel not in relacionamento.papeis_ativos:
            self.add_error('papel', 'Papel inválido.')
        return self.cleaned_data.get('papel')

    def clean_senha(self):
        usuario_autenticado = authenticate(username=self.request.user.username, password=self.cleaned_data.get('senha'))
        if not usuario_autenticado:
            raise forms.ValidationError('Senha inválida')
        return self.cleaned_data.get('senha')


class ServicoGerenteEquipeLocalForm(forms.ModelFormPlus):
    class Meta:
        model = ServicoGerenteEquipeLocal
        fields = ('servico', 'campus', 'vinculo')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['campus'].queryset = UnidadeOrganizacional.objects.uo()


def ServicoGerenteFormFactory(servico):
    class ServicoGerenteForm(forms.ModelFormPlus):
        class Meta:
            model = Servico
            fields = ('titulo',)

        def __init__(self, *args, **kwargs):
            self.instance = servico
            super().__init__(*args, **kwargs)
            self.fields['titulo'].widget = forms.TextInput(attrs=dict(readonly='readonly'))

    return ServicoGerenteForm


def AdicionarUsuarioEquipeFormFactory(usuario, uo):
    class AdicionarUsuarioEquipeForm(forms.FormPlus):
        vinculo = forms.MultipleModelChoiceFieldPlus(
            queryset=Vinculo.objects,
            label='Usuários',
            help_text="Informe parte do Nome ou Matrícula ou CPF ou E-mail Institucional",
        )

        def __init__(self, *args, **kwargs):
            super(AdicionarUsuarioEquipeForm, self).__init__(*args, **kwargs)
            self.fields['vinculo'].queryset = Vinculo.objects.filter(
                tipo_relacionamento_id__in=ContentType.objects.filter(Q(Vinculo.SERVIDOR | Vinculo.PRESTADOR)), user__is_active=True,
            )

    return AdicionarUsuarioEquipeForm


class TestarDisponibilidadeForm(forms.FormPlus):
    METHOD = 'GET'
    cpf = forms.CharFieldPlus(required=False, label='CPF')
