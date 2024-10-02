from xml.dom import minidom
from datetime import datetime

from django.contrib.auth import authenticate

from djtools.templatetags.filters import in_group
from processo_seletivo import tasks
from comum.models import Ano
from djtools import forms
from djtools.forms.widgets import AutocompleteWidget
from djtools.testutils import running_tests
from edu.models import PERIODO_LETIVO_CHOICES, CursoCampus, Matriz, Aluno, LinhaPesquisa
from djtools.forms.wizard import FormWizardPlus
from processo_seletivo.models import (
    Lista,
    Edital,
    Candidato,
    WebService,
    EditalAdesaoCampus,
    InscricaoFiscal,
    ConfiguracaoMigracaoVaga,
    RotuloLista,
    PrecedenciaMigracao,
    CandidatoVaga,
    CriacaoVagaRemanescente,
    EditalAdesao, EditalPeriodoLiberacao, OfertaVagaCurso)
from rh.models import PessoaFisica, Servidor, UnidadeOrganizacional
from comum.utils import get_uo


class EditalForm(forms.ModelFormPlus):
    class Meta:
        models = Edital
        fields = (
            'ano', 'semestre', 'codigo', 'descricao', 'configuracao_migracao_vagas', 'matricula_no_polo', 'matricula_online'
        )

    fieldsets = (
        ('Dados Gerais', {'fields': (('ano'), ('semestre', 'codigo'), 'descricao', 'matricula_online')}),
        ('Migração de Vagas', {'fields': ('configuracao_migracao_vagas',)}),
        ('EAD', {'fields': ('matricula_no_polo',)}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.id or not Candidato.objects.filter(edital=self.instance).exclude(campus_polo__isnull=True).exclude(campus_polo='').exists():
            self.fieldsets = self.fieldsets[:-1]

    def save(self, *args, **kwargs):
        if not self.instance.pk:
            self.instance.qtd_vagas = 0
            self.instance.qtd_inscricoes = 0
            self.instance.qtd_inscricoes_confirmadas = 0
            self.instance.detalhamento_por_campus = '{}'
        return super().save(commit=True)

    def save_m2m(self):
        pass


class EditalLiberacaoForm(forms.ModelFormPlus):

    class Meta:
        model = EditalPeriodoLiberacao
        fields = ('uo', 'data_inicio_matricula', 'data_fim_matricula', 'data_limite_avaliacao')

    def __init__(self, *args, **kwargs):
        edital = kwargs.pop('edital')
        uos_edital = kwargs.pop('uos_edital')
        uos_cadastradas = list(EditalPeriodoLiberacao.objects.filter(edital=edital).values_list('uo', flat=True))

        super().__init__(*args, **kwargs)

        if self.instance.pk:
            if self.instance.uo_id in uos_cadastradas:
                uos_cadastradas.remove(self.instance.uo_id)

        self.instance.edital = edital
        self.instance.usuario = self.request.user

        if self.instance.pk:
            self.fields['uo'].queryset = UnidadeOrganizacional.objects.filter(pk=self.instance.uo_id)
        else:
            self.fields['uo'].queryset = UnidadeOrganizacional.objects.filter(pk__in=uos_edital).exclude(pk__in=uos_cadastradas)


class EditalAusentarCandidatosForm(forms.FormPlus):
    campus = forms.ModelChoiceFieldPlus(label='Campus', required=True, queryset=UnidadeOrganizacional.objects)
    chamada = forms.ChoiceField(label='Número da Chamada', required=True)
    confirmacao = forms.BooleanField(label='Confirma o Processamento?', required=True)
    senha = forms.CharFieldPlus(label='Senha para Confirmação', required=True, widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        edital = kwargs.pop('edital')
        super().__init__(*args, **kwargs)

        candidatos_vaga = CandidatoVaga.objects.filter(
            candidato__edital=edital,
            situacao__isnull=True,
            convocacao__isnull=False
        ).values('convocacao').order_by().distinct()

        self.fields['chamada'].choices = [[x['convocacao'], x['convocacao']] for x in candidatos_vaga]

        if in_group(self.request.user, 'Administrador Acadêmico'):
            uos = OfertaVagaCurso.locals.filter(edital=edital).values_list('curso_campus__diretoria__setor__uo', flat=True)
            self.fields['campus'].queryset = UnidadeOrganizacional.objects.filter(pk__in=uos)
        else:
            vinculo = self.request.user.get_vinculo()
            self.fields['campus'].queryset = UnidadeOrganizacional.objects.filter(pk=vinculo.setor.uo_id)

    def clean_senha(self):
        senha = self.cleaned_data['senha']
        if senha:
            usuario_autenticado = authenticate(username=self.request.user.username, password=senha)
            if not usuario_autenticado:
                raise forms.ValidationError('Senha inválida')
        return self.cleaned_data.get('senha')


class ImportarEditalXMLForm(forms.FormPlus):

    xml = forms.FileFieldPlus(label='Arquivo XML', required=True)

    fieldsets = (('Importação', {'fields': ('xml',)}),)

    def processar(self, edital):
        xml = self.cleaned_data.get('xml')
        Aluno.objects.filter(candidato_vaga__oferta_vaga__oferta_vaga_curso__edital=edital).update(candidato_vaga=None)
        edital.lista_set.all().delete()
        edital.ofertavagacurso_set.all().delete()
        edital.candidato_set.all().delete()
        return tasks.importar_edital(xml.read().decode(), edital)


class EditarOfertaVagaCursoForm(forms.ModelFormPlus):
    curso_campus = forms.ModelChoiceFieldPlus(CursoCampus.objects, label='Curso')

    class Meta:
        model = OfertaVagaCurso
        fields = 'curso_campus',

    def save(self, *args, **kwargs):
        retorno = super().save(*args, **kwargs)
        Candidato.objects.filter(candidatovaga__oferta_vaga__oferta_vaga_curso=self.instance).update(curso_campus=self.instance.curso_campus)
        return retorno


class ImportarEditalForm(FormWizardPlus):
    ano = forms.ModelChoiceField(Ano.objects.all(), label='Ano', required=True)
    semestre = periodo_letivo = forms.ChoiceField(choices=[[0, '----']] + PERIODO_LETIVO_CHOICES, label='Semestre', required=True)
    webservice = forms.ModelChoiceField(WebService.objects.all(), label='WebService', required=True)
    configuracao_migracao_vagas = forms.ModelChoiceField(ConfiguracaoMigracaoVaga.objects.all(), required=False)

    edital = forms.ChoiceField(choices=[], label='Edital', widget=forms.Select(attrs=dict(style='width:600px')))

    steps = (
        [
            ('Fonte de Dados', {'fields': ('webservice',)}),
            ('Período Letivo', {'fields': ('ano', 'semestre')}),
            ('Migração de Vagas Remanescentes', {'fields': ('configuracao_migracao_vagas',)}),
        ],
        [('Seleção do Edital', {'fields': ('edital',)})],
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def next_step(self):
        if 'edital' in self.fields:
            self.fields['edital'].choices = self.get_editais_choices()

    def clean(self):
        return self.cleaned_data

    def clean_edital(self):
        codigo_edital = self.cleaned_data['edital']
        try:
            self.xml = self.get_entered_data('webservice').edital(codigo_edital)
        except BaseException:
            raise forms.ValidationError('Problemas ao tentar conectar com o Sistema de Gerenciamento de Concursos (SGC) ou equivalente.')
        doc = minidom.parseString(self.xml)
        codigos_cursos = []
        codigos_cursos_invalidos = []
        for _codigo_curso in doc.getElementsByTagName('codigo-curso'):
            codigo_curso = _codigo_curso.firstChild and _codigo_curso.firstChild.nodeValue or 0
            codigos_cursos.append(codigo_curso)
        for codigo_curso in list(set(codigos_cursos)):
            if not CursoCampus.objects.filter(codigo=codigo_curso).exists():
                codigos_cursos_invalidos.append(str(codigo_curso))
        if codigos_cursos_invalidos:
            raise forms.ValidationError(
                'Os cursos com códigos %s cadastrados no sistema de gerenciamento de concurso não possuem cursos correspondentes no SUAP. Cadastre-os antes de realizar a importação.'
                % codigos_cursos_invalidos
            )

        linhas_pesquisa = []
        linhas_pesquisa_invalidas = []
        for _linha_pesquisa in doc.getElementsByTagName('linha-pesquisa'):
            linha_pesquisa = _linha_pesquisa.firstChild and _linha_pesquisa.firstChild.nodeValue or 0
            if linha_pesquisa:
                linhas_pesquisa.append(linha_pesquisa)
        if running_tests():
            linhas_pesquisa = LinhaPesquisa.objects.all().values_list('pk', flat=True)
        for linha_pesquisa in list(set(linhas_pesquisa)):
            if not LinhaPesquisa.objects.filter(pk=linha_pesquisa).exists():
                linhas_pesquisa_invalidas.append(str(linha_pesquisa))
        if linhas_pesquisa_invalidas:
            raise forms.ValidationError(
                'As linhas de pesquisa com códigos %s cadastrados no sistema de gerenciamento de concurso não possuem linha de pesquisa correspondentes no SUAP. Cadastre-os no suap antes de realizar a importação.'
                % linhas_pesquisa_invalidas
            )

        return codigo_edital

    def get_editais_choices(self):
        '''
        Este método retorna um choices contendo todos os editais disponibilizados pelo webservices do SGC. O usuário irá
        escolhar um dos editais para ser importado.

        Abaixo temos um exemplo do XML retornado pelo serviço do SGC que retornar os editais.

        <editais>
            <edital>
                <codigo>39</codigo>
                <descricao>EDITAL N 09/2016-PROEN/IFRN - Aperfeiçoamento para Professores dos Municípios do Rio Grande do Norte (CAPROM)</descricao>
                <ano>2016</ano>
                <semestre>1</semestre>
                <remanescentes>Não</remanescentes>
                <sisu>Não</sisu>
                <qtd_vagas>60</qtd_vagas>
                <qtd_inscricoes>153</qtd_inscricoes>
                <qtd_inscricoes_confirmadas>24</qtd_inscricoes_confirmadas>
                <detalhamento_por_campus>
                    [{"qtd_inscricoes": 125, "suap_unidade_organizacional_id": "14", "campus": "EaD", "qtd_inscricoes_confirmadas": 18, "qtd_vagas": 30}, {"qtd_inscricoes": 28, "suap_unidade_organizacional_id": "14", "campus": "Polo SC", "qtd_inscricoes_confirmadas": 6, "qtd_vagas": 30}]
                </detalhamento_por_campus>
            </edital>
            <edital>
            ...
            </edital>
        </editais>


        :return:
        '''

        self.editais_disponiveis_webservices = dict()

        lista = []
        ano_selecionado = self.get_entered_data('ano')
        semestre_selecionado = self.get_entered_data('semestre')
        if ano_selecionado and semestre_selecionado:
            semestre_selecionado = int(semestre_selecionado)
            if self.get_entered_data('webservice').url_editais:
                xml = self.get_entered_data('webservice').editais()
                doc = minidom.parseString(xml)
                for _edital in doc.getElementsByTagName('edital'):
                    codigo = _edital.getElementsByTagName('codigo')[0].firstChild.nodeValue
                    ano = _edital.getElementsByTagName('ano')[0].firstChild.nodeValue
                    semestre = _edital.getElementsByTagName('semestre')[0].firstChild.nodeValue
                    remanescentes = _edital.getElementsByTagName('remanescentes')[0].firstChild.nodeValue == 'Sim'

                    sisu = _edital.getElementsByTagName('sisu')[0].firstChild.nodeValue == 'Sim'
                    qtd_vagas = _edital.getElementsByTagName('qtd_vagas')[0].firstChild.nodeValue
                    qtd_inscricoes = _edital.getElementsByTagName('qtd_inscricoes')[0].firstChild.nodeValue
                    qtd_inscricoes_confirmadas = _edital.getElementsByTagName('qtd_inscricoes_confirmadas')[0].firstChild.nodeValue
                    detalhamento_por_campus = _edital.getElementsByTagName('detalhamento_por_campus')[0].firstChild.nodeValue

                    # Se o _edital corrente tiver o mesmo ano e semestre especificados pelo usuário, então ele será montada
                    # uma descrição e este edital estará dispoível para seleção.
                    if (not ano_selecionado or str(ano) == str(ano_selecionado.ano)) and (not semestre_selecionado or str(semestre) == str(semestre_selecionado)):
                        if _edital.getElementsByTagName('descricao')[0].firstChild:
                            descricao = '{} de {}/{}'.format(_edital.getElementsByTagName('descricao')[0].firstChild.nodeValue, ano, semestre)
                        else:
                            descricao = 'Edital {} de {}/{}'.format(codigo, ano, semestre)
                        lista.append([int(codigo), '{} {}'.format(descricao, remanescentes and '(Vagas Remanescentes)' or '')])

                        # Criando um objeto Edital sem persistí-lo.
                        edital_add = Edital(
                            codigo=codigo,
                            descricao=descricao,
                            remanescentes=remanescentes,
                            sisu=sisu,
                            qtd_vagas=qtd_vagas,
                            qtd_inscricoes=qtd_inscricoes,
                            qtd_inscricoes_confirmadas=qtd_inscricoes_confirmadas,
                            detalhamento_por_campus=detalhamento_por_campus,
                        )
                        # Adicionando o objeto Edital dentro do dicionário que irá armzenar todos os editais disponíveis
                        # para a seleção pelo usuário.
                        self.editais_disponiveis_webservices[codigo] = edital_add

        return lista

    def processar(self, request):
        # Campos do formulário
        codigo_edital = self.cleaned_data['edital']
        configuracao_migracao_vagas = self.cleaned_data['configuracao_migracao_vagas']
        ano = self.cleaned_data['ano']
        semestre = int(self.cleaned_data['semestre'])
        webservice = self.cleaned_data['webservice']

        # Edital "não persistido" selecionado.
        edital_selecionado_webservice = self.editais_disponiveis_webservices[codigo_edital]
        # Complementando algumas informações do Edital "não persistido" selecionado para que ele possa ser persistido
        # mais tarde, seja via INSERT ou UPDATE.
        edital_selecionado_webservice.ano = ano
        edital_selecionado_webservice.semestre = semestre
        edital_selecionado_webservice.webservice = webservice
        # Verificando se o edital já encontra-se persistido. Se sim, ocorrerá uma atualização dos dados, caso contrário
        # uma inserção. A entidade Edital tem uma PK normal, mas uma outra chave única que pode ser usada é o
        # código + webservice.
        qs = Edital.objects.filter(codigo=codigo_edital, webservice=webservice)
        if qs.exists():
            edital = qs[0]
            edital.configuracao_migracao_vagas = configuracao_migracao_vagas
            # edital.codigo = edital_selecionado_webservice.codigo
            edital.descricao = edital_selecionado_webservice.descricao
            edital.ano = edital_selecionado_webservice.ano
            edital.semestre = edital_selecionado_webservice.semestre

            edital.sisu = edital_selecionado_webservice.sisu
            edital.qtd_vagas = edital_selecionado_webservice.qtd_vagas
            edital.qtd_inscricoes = edital_selecionado_webservice.qtd_inscricoes
            edital.qtd_inscricoes_confirmadas = edital_selecionado_webservice.qtd_inscricoes_confirmadas
            edital.detalhamento_por_campus = edital_selecionado_webservice.detalhamento_por_campus

            edital.remanescentes = edital_selecionado_webservice.remanescentes
            # edital.webservice = edital_selecionado_webservice.webservice
            edital.save()
        else:
            # Senão, ocorrerá uma inserção, já que o edital "bruto" não tem id.
            edital_selecionado_webservice.configuracao_migracao_vagas = configuracao_migracao_vagas
            edital_selecionado_webservice.save()
            edital = edital_selecionado_webservice
        return tasks.importar_edital(self.xml, edital)


class MatricularAlunoProitecForm(forms.FormPlus):
    edital = forms.CharField(widget=forms.HiddenInput())
    ano = forms.ModelChoiceField(Ano.objects.all(), label='Ano', required=True)
    periodo = forms.ChoiceField(choices=[[0, '----']] + PERIODO_LETIVO_CHOICES, label='Período', required=True)
    matriz = forms.ModelChoiceField(queryset=Matriz.objects.none(), label='Matriz', required=True)

    SUBMIT_LABEL = 'Matricular Candidatos'

    def __init__(self, edital, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['edital'].initial = edital.pk
        self.fields['matriz'].queryset = edital.get_matrizes_pronatec()
        self.edital = edital

    def processar(self, request):
        edital = Edital.objects.get(pk=self.cleaned_data.get('edital'))
        ano_letivo = self.cleaned_data.get('ano')
        periodo_letivo = self.cleaned_data.get('periodo')
        matriz = self.cleaned_data.get('matriz')
        return tasks.matricular_alunos_proitec(edital, ano_letivo, periodo_letivo, matriz)


class ListaForm(forms.ModelFormPlus):
    class Meta:
        model = Lista
        fields = ('forma_ingresso',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['forma_ingresso'].queryset = self.fields['forma_ingresso'].queryset.filter(ativo=True)


class EditalAdesaoCampusForm(forms.ModelForm):
    idade_minima = forms.BooleanField(label='Critério de Maioridade', required=False)

    class Meta:
        model = EditalAdesaoCampus
        fields = (
            'nome',
            'edital_regulador',
            'data_inicio_inscricoes',
            'data_encerramento_inscricoes',
            'ano_edital',
            'numero_edital',
            'campus',
            'data_aplicacao_prova',
            'idade_minima',
            'data_aplicacao_prova',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not running_tests():
            now = datetime.now()
            self.fields['edital_regulador'].queryset = self.fields['edital_regulador'].queryset.filter(data_inicio_adesao__lte=now, data_limite_adesao__gte=now)
        else:
            self.fields['edital_regulador'].queryset = EditalAdesao.objects.all()
        self.fields['campus'].queryset = UnidadeOrganizacional.objects.uo()

    def clean(self):
        cleaned_data = super().clean()
        data_encerramento_inscricoes = cleaned_data['data_encerramento_inscricoes']
        edital_regulador = cleaned_data.get('edital_regulador', None)
        if edital_regulador and data_encerramento_inscricoes > edital_regulador.data_limite_adesao:
            raise forms.ValidationError("A data de encerramento das inscrições não pode " "ser superior a data limite de adesão ao edital regulador!")

        idade_minima = cleaned_data.get('idade_minima', False)
        data_aplicacao_prova = cleaned_data.get('data_aplicacao_prova', None)
        if idade_minima:
            if not data_aplicacao_prova:
                raise forms.ValidationError("O edital exige uma data mínima para a inscrição dos fiscais, portanto" " a data da aplicação da prova deve ser informada!")

            if data_encerramento_inscricoes.date() > data_aplicacao_prova.date():
                raise forms.ValidationError("A data de encerramento das inscrições não pode " "ser superior a data da aplicação da prova!")
        return cleaned_data


class InscricaoFiscalForm(forms.ModelFormPlus):
    class Meta:
        model = InscricaoFiscal
        exclude = ('pessoa_fisica', 'matricula', 'edital', 'campus')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.edital = kwargs.pop('edital')
        self.campus = get_uo(self.user)
        super().__init__(*args, **kwargs)
        self.instance.set_user(self.user)
        self.instance.edital = self.edital
        self.instance.campus = self.campus

        pessoa_fisica = self.user.get_profile()
        choices = []
        servidor = Servidor.objects.efetivos().filter(cpf=pessoa_fisica.cpf, excluido=False).first()
        if servidor:
            choices.append((InscricaoFiscal.TIPO_SERVIDOR, 'Servidor'))
        aluno = Aluno.objects.filter(pessoa_fisica__cpf=pessoa_fisica.cpf, situacao__ativo=True).exists()
        if aluno:
            choices.append((InscricaoFiscal.TIPO_ALUNO, 'Aluno'))
        self.fields['tipo'] = forms.ChoiceField(choices=choices, label='Tipo do Vínculo')

    def clean(self, *args, **kwargs):

        self.cleaned_data = super().clean(*args, **kwargs)

        tipo_vinculo = self.cleaned_data.get('tipo', None)
        if tipo_vinculo is None:
            raise forms.ValidationError('O tipo do vínculo ser informado')
        self.instance.tipo = tipo_vinculo
        tipo_conta = self.cleaned_data.get('tipo_conta', None)
        if tipo_conta is None:
            raise forms.ValidationError('O tipo da conta deve ser informado')

        if self.cleaned_data['tipo_conta'] == InscricaoFiscal.TIPO_CONTA_POUPANCA:
            if not self.cleaned_data['operacao']:
                raise forms.ValidationError('A operação deve ser informada no caso do tipo da conta ' 'ser Poupança')
        if not self.cleaned_data['aceito_termos']:
            raise forms.ValidationError('A inscrição só pode ser validada caso o termo de ' 'compromisso for aceito')

        pode_efetuar_inscricao, msg = InscricaoFiscal.pode_efetuar_inscricao(self.user, self.edital)
        if not pode_efetuar_inscricao:
            raise forms.ValidationError(msg)

        return self.cleaned_data


class InscricaoFiscalAdminForm(forms.ModelFormPlus):
    pessoa_fisica = forms.ModelChoiceField(label='Servidor/Aluno', queryset=PessoaFisica.objects, widget=AutocompleteWidget(search_fields=PessoaFisica.SEARCH_FIELDS))

    class Meta:
        model = InscricaoFiscal
        fields = (
            'edital',
            'pessoa_fisica',
            'tipo',
            'matricula',
            'telefones',
            'banco',
            'numero_agencia',
            'tipo_conta',
            'numero_conta',
            'operacao',
            'pis_pasep',
            'outros_processos',
            'aceito_termos',
        )

    def clean(self, *args, **kwargs):

        self.cleaned_data = super().clean(*args, **kwargs)

        tipo_vinculo = self.cleaned_data.get('tipo', None)
        if tipo_vinculo is None:
            raise forms.ValidationError('O tipo do vínculo ser informado')
        self.instance.tipo = tipo_vinculo
        tipo_conta = self.cleaned_data.get('tipo_conta', None)
        if tipo_conta is None:
            raise forms.ValidationError('O tipo da conta deve ser informado')

        if self.cleaned_data['tipo_conta'] == InscricaoFiscal.TIPO_CONTA_POUPANCA:
            if not self.cleaned_data['operacao']:
                raise forms.ValidationError('A operação deve ser informada no caso do tipo da conta ' 'ser Poupança')
        if not self.cleaned_data['aceito_termos']:
            raise forms.ValidationError('A inscrição só pode ser validada caso o termo de ' 'compromisso for aceito')

        pode_efetuar_inscricao, msg = InscricaoFiscal.pode_efetuar_inscricao(self.user, self.edital)
        if not pode_efetuar_inscricao:
            raise forms.ValidationError(msg)

        return self.cleaned_data


class ConfiguracaoMigracaoVagaForm(forms.ModelFormPlus):
    listas = forms.ModelMultiplePopupChoiceField(RotuloLista.objects.all(), label='Listas', required=True)

    class Meta:
        model = ConfiguracaoMigracaoVaga
        fields = 'descricao', 'is_sisu', 'ativo', 'listas'

    fieldsets = (('Dados Gerais', {'fields': ('descricao', ('is_sisu', 'ativo'))}), ('Listas Utilizadas', {'fields': ('listas',)}))


class DefinirConfiguracaoMigracaoVagaForm(forms.ModelFormPlus):
    class Meta:
        model = Edital
        fields = ('configuracao_migracao_vagas',)


class DefinirPrecedenciaMatriculaForm(forms.ModelFormPlus):
    class Meta:
        model = ConfiguracaoMigracaoVaga
        exclude = 'descricao', 'is_sisu', 'ativo', 'listas'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for i in range(1, 16):
            self.fields['lista_{}'.format(i)].queryset = self.instance.listas.all()
        qtd = self.instance.listas.count() + 1
        self.fieldsets = (('Precedência de Matrícula', {'fields': ['lista_{}'.format(i) for i in range(1, qtd)]}),)


class PrecedenciaMigracaoForm(forms.FormPlus):
    TITLE = 'Precedência de Migração'
    origem = forms.ModelChoiceField(RotuloLista.objects, label='Lista')

    def __init__(self, *args, **kwargs):
        self.configuracao = kwargs.pop('configuracao')
        origem = 'lista_origem' in kwargs and kwargs.pop('lista_origem') or None
        super().__init__(*args, **kwargs)
        self.fields['origem'].queryset = self.configuracao.listas.all()
        qtd = self.configuracao.listas.count()
        lista = []
        for i in range(1, qtd):
            lista.append(str(i))
            self.fields[str(i)] = forms.ModelChoiceField(self.configuracao.listas.all(), label='Ordem {}'.format(i), required=False)
            if origem:
                qs = PrecedenciaMigracao.objects.filter(configuracao=self.configuracao, origem__nome=origem, precedencia=i)
                if qs.exists():
                    self.initial[str(i)] = qs[0].destino.pk

        self.fieldsets = (('Dados Gerais', {'fields': ('origem',)}), ('Ordem de Precedência', {'fields': lista}))
        pks = PrecedenciaMigracao.objects.filter(configuracao=self.configuracao).values_list('origem', flat=True)
        if origem:
            pk = RotuloLista.objects.get(nome=origem).pk
            self.initial['origem'] = pk
            self.fields['origem'].queryset = self.fields['origem'].queryset.filter(pk=pk)
        else:
            self.fields['origem'].queryset = self.fields['origem'].queryset.exclude(pk__in=pks)

    def save(self):
        origem = self.cleaned_data.get('origem')
        PrecedenciaMigracao.objects.filter(configuracao=self.configuracao, origem=origem).delete()
        qtd = self.configuracao.listas.count()
        for i in range(1, qtd):
            destino = self.cleaned_data.get(str(i))
            if destino:
                PrecedenciaMigracao.objects.create(configuracao=self.configuracao, origem=origem, precedencia=i, destino=destino)
            else:
                break


class RealizarAcaoLote(forms.FormPlus):
    acao = forms.ChoiceField(label='Ação', choices=[['ausencia', 'Registrar Ausência'], ['inaptidao', 'Registrar Inaptidão']])
    classificacao_inicial = forms.IntegerField(label='Classificação Inicial')
    classificacao_final = forms.IntegerField(label='Classificação Final')

    def __init__(self, *args, **kwargs):
        self.oferta_vaga = kwargs.pop('oferta_vaga')
        super().__init__(*args, **kwargs)

        if self.request.user.is_superuser:
            self.fields['acao'].choices = self.fields['acao'].choices + [['simular_matricula', 'Simular Matrícula']]

    def processar(self):
        classificacao_inicial = self.cleaned_data['classificacao_inicial']
        classificacao_final = self.cleaned_data['classificacao_final']
        acao = self.cleaned_data['acao']
        qs = self.oferta_vaga.get_candidatos_convocados().filter(situacao__isnull=True, classificacao__gte=classificacao_inicial, classificacao__lte=classificacao_final)
        if acao == 'ausencia':
            for candidato_vaga in qs:
                candidato_vaga.registrar_ausencia()
        elif acao == 'inaptidao':
            for candidato_vaga in qs:
                candidato_vaga.registrar_inaptidao()
        elif acao == 'simular_matricula':
            for candidato_vaga in qs:
                candidato_vaga.simular_matricula()

    def clean(self):
        cleaned_data = self.cleaned_data
        classificacao_inicial = self.cleaned_data['classificacao_inicial'] or 0
        classificacao_final = self.cleaned_data['classificacao_final'] or 0
        qs = self.oferta_vaga.get_candidatos_convocados().filter(classificacao__gte=classificacao_inicial, classificacao__lte=classificacao_final)
        if qs.filter(situacao__isnull=False):
            raise forms.ValidationError('O intervalo informado inclui inscrições já processadas. Por favor, informe outro intervalo de classificação.')
        return cleaned_data


class VincularMatriculaForm(forms.FormPlus):
    aluno = forms.ModelChoiceField(queryset=Aluno.objects.none(), label='Aluno', required=True)

    SUBMIT_LABEL = 'Vincular'

    def __init__(self, *args, **kwargs):
        self.candidato_vaga = kwargs.pop('candidato_vaga')
        super().__init__(*args, **kwargs)
        self.fields['aluno'].queryset = Aluno.objects.filter(
            pessoa_fisica__cpf=self.candidato_vaga.candidato.cpf,
            curso_campus=self.candidato_vaga.candidato.curso_campus,
            ano_letivo=self.candidato_vaga.candidato.edital.ano,
            periodo_letivo=self.candidato_vaga.candidato.edital.semestre,
        )

    def processar(self):
        self.candidato_vaga.situacao = CandidatoVaga.MATRICULADO
        self.candidato_vaga.save()
        aluno = self.cleaned_data.get('aluno')
        aluno.candidato_vaga = self.candidato_vaga
        aluno.save()


class CriacaoVagaRemanescenteForm(forms.ModelFormPlus):
    class Meta:
        model = CriacaoVagaRemanescente
        fields = 'qtd', 'justificativa'
