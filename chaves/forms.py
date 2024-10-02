from django.db.models import Q

from chaves.models import Chave, Movimentacao
from comum.models import Sala, PrestadorServico, User
from comum.utils import get_uo
from djtools import forms
from djtools.forms.widgets import AutocompleteWidget
from djtools.forms.widgets import FilteredSelectMultiplePlus
from edu.models import Aluno
from rh.models import UnidadeOrganizacional, PessoaFisica, Pessoa, Setor, Servidor


class ChaveForm(forms.ModelFormPlus):
    pessoas = forms.MultipleModelChoiceFieldPlus(
        required=False,
        queryset=PessoaFisica.objects.filter(Q(tem_digital_fraca=True) | Q(template__isnull=False)),
        help_text='Somente ser&atilde;o exibidas as pessoas que possuem digital cadastrada ou permiss&atilde;o \
                              para pegar a chave sem a digital.<br/>Caso a pessoa n&atilde;o seja exibida, oriente-a para procurar \
                              o setor respons&aacute;vel pelo cadastro da digital.',
    )
    sala = forms.ModelChoiceField(required=True, queryset=Sala.ativas.order_by('predio__uo'), widget=AutocompleteWidget(search_fields=Sala.SEARCH_FIELDS))

    class Meta:
        model = Chave
        exclude = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.request.user

        if user.has_perm('chaves.poder_ver_do_campus'):
            self.fields['sala'].queryset = Sala.ativas.filter(predio__uo=get_uo(user))
        else:
            salas_permitidas = Sala.ativas.filter(avaliadores_de_agendamentos=user)
            self.fields['sala'].queryset = Sala.ativas.filter(id__in=salas_permitidas.values_list('id', flat=True)).order_by('nome')

        PessoaFisica.get_ext_combo_template = get_ext_combo_template

    def clean_identificacao(self):
        """
        Verifica se já existe uma chave com a identificação no Campus
        """
        if self.data.get('sala'):
            uo_da_chave = UnidadeOrganizacional.objects.suap().filter(predio__sala=self.data['sala'])
            id = self.instance.id
            chaves_da_uo = Chave.objects.filter(sala__predio__uo=uo_da_chave[0], identificacao=self.cleaned_data['identificacao']).exclude(id=id)
            if chaves_da_uo:
                raise forms.ValidationError('Já existe a chave ' + self.cleaned_data['identificacao'] + ' no Campus ' + uo_da_chave[0].setor.sigla + '.')

            return self.cleaned_data['identificacao']


def get_ext_combo_template(self):
    out = [f'<dt class="sr-only">Nome</dt><dd><strong>{self.pessoa_ptr}</strong></dd>']
    if hasattr(self, 'servidor'):
        if self.servidor.setor:
            out.append(f'<dt class="sr-only">Setor</dt><dd>{self.servidor.setor.get_caminho_as_html()}</dd>')
        if self.servidor.cargo_emprego:
            out.append(f'<dt class="sr-only">Cargo</dt><dd>{self.servidor.cargo_emprego}</dd>')
    template = '''<div class="person">
        <div class="photo-circle">
            <img alt="Foto de {}" src="{}" />
        </div>
        <dl>{}</dl>
    </div>
    '''.format(
        self.pessoa_ptr, self.get_foto_75x100_url(), ''.join(out)
    )
    return template


class MovimentacaoAdminForm(forms.ModelFormPlus):
    pessoa_emprestimo = forms.ModelChoiceField(queryset=Pessoa.objects.all(), widget=AutocompleteWidget(search_fields=Pessoa.SEARCH_FIELDS), label='Pessoa Empréstimo')
    operador_emprestimo = forms.ModelChoiceField(queryset=Pessoa.objects.all(), widget=AutocompleteWidget(search_fields=Pessoa.SEARCH_FIELDS), label='Operador Empréstimo')
    pessoa_devolucao = forms.ModelChoiceField(queryset=Pessoa.objects.all(), widget=AutocompleteWidget(search_fields=Pessoa.SEARCH_FIELDS), label='Pessoa Devolução')
    operador_devolucao = forms.ModelChoiceField(queryset=Pessoa.objects.all(), widget=AutocompleteWidget(search_fields=Pessoa.SEARCH_FIELDS), label='Operador Devolução')

    class Meta:
        model = Movimentacao
        exclude = ()


class MovimentacaoChaveForm(forms.FormPlus):
    METHOD = 'GET'
    data_inicio = forms.DateFieldPlus(label='Data Inicial', required=True)
    data_termino = forms.DateFieldPlus(label='Data Final', required=True)
    chave = forms.IntegerField(required=False, widget=forms.HiddenInput())


class BuscarUsuarioChaveForm(forms.FormPlus):
    TODOS = 0
    TEC_ADM = 1
    DOCENTE = 2
    PRESTADOR_SERVICO = 3
    ALUNO = 4
    VINCULO_CHOICES = ((TODOS, 'Todos'), (TEC_ADM, 'Técnico Administrativo'), (DOCENTE, 'Docente'), (PRESTADOR_SERVICO, 'Prestador de Serviço'), (ALUNO, 'Aluno'))

    METHOD = 'GET'
    SUBMIT_LABEL = 'Buscar'
    nome = forms.CharField(label='Nome ou Matrícula', required=True, widget=forms.TextInput(attrs={'size': 20}))
    vinculo = forms.ChoiceField(label='Vínculo', required=False, choices=VINCULO_CHOICES)
    campus = forms.ModelChoiceField(UnidadeOrganizacional.objects.suap(), label='Campus', required=False)

    class Media:
        js = ['/static/chaves/js/buscarusuarioform.js']

    def processar(self):
        nome = self.cleaned_data.get("nome")
        vinculo = int(self.cleaned_data.get("vinculo") or "0")
        campus = self.cleaned_data.get("campus")
        vinculos = []
        if vinculo:
            if vinculo in [BuscarUsuarioChaveForm.TEC_ADM, BuscarUsuarioChaveForm.DOCENTE]:
                vinculos = Servidor.objects.filter(Q(nome__icontains=nome) | Q(matricula__icontains=nome))
                if vinculo == BuscarUsuarioChaveForm.TEC_ADM:
                    vinculos = vinculos.filter(cargo_emprego__grupo_cargo_emprego__categoria='tecnico_administrativo')
                else:
                    vinculos = vinculos.filter(cargo_emprego__grupo_cargo_emprego__categoria='docente')
                if campus:
                    vinculos = vinculos.filter(setor__uo=campus)
                vinculos = vinculos.values_list('user__id', flat=True)
            elif vinculo == BuscarUsuarioChaveForm.PRESTADOR_SERVICO:
                vinculos = PrestadorServico.objects.filter(Q(nome__icontains=nome) | Q(matricula__icontains=nome))
                if campus:
                    vinculos = vinculos.filter(setor__uo=campus)
                vinculos = vinculos.values_list('user__id', flat=True)
            elif vinculo == BuscarUsuarioChaveForm.ALUNO:
                vinculos = Aluno.objects.filter(Q(pessoa_fisica__nome__icontains=nome) | Q(matricula__icontains=nome))
                if campus:
                    vinculos = vinculos.filter(curso_campus__diretoria__setor__uo=campus)
                vinculos = vinculos.values_list('vinculos__user__id', flat=True)
            return User.objects.filter(id__in=vinculos)
        else:
            return User.objects.filter(Q(pessoafisica__nome__icontains=nome) | Q(username__icontains=nome))


class AdicionarChaveForm(forms.FormPlus):
    chaves = forms.MultipleModelChoiceFieldPlus(label='Chaves', queryset=Chave.objects, widget=FilteredSelectMultiplePlus('', True))

    def __init__(self, *args, **kwargs):
        pessoa_fisica = kwargs.pop('pessoa_fisica')
        user = kwargs['request'].user
        queryset = Chave.objects.all()
        if user.has_perm('chaves.poder_ver_do_campus'):
            queryset = Chave.objects.filter(sala__predio__uo=get_uo(user))

        kwargs['initial'] = {'chaves': queryset.filter(id__in=pessoa_fisica.chave_set.all()).values_list('id', flat=True)[::1]}

        super().__init__(*args, **kwargs)

        user = self.request.user
        if user.has_perm('chaves.poder_ver_todas'):
            self.fields['chaves'].queryset = Chave.objects.all()
        elif user.has_perm('chaves.poder_ver_do_campus'):
            self.fields['chaves'].queryset = Chave.objects.filter(sala__predio__uo=get_uo(user))

        servidor = user.get_relacionamento()
        servidor.chave_set.values_list('id', flat=True)

    def processar(self, pessoa):
        chaves = self.cleaned_data.get('chaves')
        chaves_cadastradas = pessoa.chave_set.all()
        for chave in chaves:
            chave.pessoas.add(pessoa)
        for chave_antiga in chaves_cadastradas:
            if chave_antiga not in chaves:
                chave_antiga.pessoas.remove(pessoa)


class CopiarUsuariosChaveForm(forms.FormPlus):
    chave_origem = forms.ModelChoiceField(
        required=True, label='Chave de Origem', queryset=Chave.objects.filter(ativa=True).order_by('sala__predio__uo'), widget=AutocompleteWidget(search_fields=Chave.SEARCH_FIELDS)
    )
    chave_destino = forms.ModelChoiceField(
        required=True,
        label='Chave de Destino',
        queryset=Chave.objects.filter(ativa=True).order_by('sala__predio__uo'),
        widget=AutocompleteWidget(search_fields=Chave.SEARCH_FIELDS),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.request.user

        self.fields['chave_origem'].queryset = Chave.objects.filter(sala__predio__uo=get_uo(user)).order_by('identificacao')
        if user.has_perm('chaves.poder_ver_do_campus'):
            self.fields['chave_destino'].queryset = Chave.objects.filter(sala__predio__uo=get_uo(user)).order_by('identificacao')
        else:
            salas_permitidas = Sala.ativas.filter(avaliadores_de_agendamentos=user)
            self.fields['chave_destino'].queryset = Chave.objects.filter(sala_id__in=salas_permitidas.values_list('id', flat=True)).order_by('identificacao')

    def clean(self):
        cleaned_data = self.cleaned_data
        chave_origem = cleaned_data.get('chave_origem')
        if not chave_origem or not chave_origem.pessoas.exists():
            self.add_error('chave_origem', 'Esta chave não possui nenhuma pessoa associada.')

        return cleaned_data


class ListarUsuariosChaveForm(forms.FormPlus):
    def __init__(self, *args, **kwargs):
        chave_origem = kwargs.pop('chave_origem', None)
        chave_destino = kwargs.pop('chave_destino', None)
        ids_pessoas_chave_destino = chave_destino.pessoas.values_list('pk', flat=True)
        ids_pessoas = chave_origem.pessoas.exclude(id__in=ids_pessoas_chave_destino).values_list('pk', flat=True)
        super().__init__(*args, **kwargs)
        self.fields['pessoas'] = forms.ModelMultipleChoiceField(
            label='Pessoas da Chave de Origem',
            queryset=PessoaFisica.objects.filter(id__in=ids_pessoas),
            widget=FilteredSelectMultiplePlus('', True),
            help_text='Excluindo as pessoas que já tem acesso a chave de destino',
        )


class SetorChaveForm(forms.FormPlus):
    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.suap().all().order_by('sigla'), label='Filtrar Setor por Campus', required=False)
    setor = forms.ChainedModelChoiceField(
        Setor.suap, label='Setor:', empty_label='Selecione o Campus', initial='Todos', required=True, obj_label='sigla', form_filters=[('uo', 'uo__id')]
    )

    chaves = forms.MultipleModelChoiceFieldPlus(label='Chaves', queryset=Chave.objects, widget=FilteredSelectMultiplePlus('', True))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.request.user

        if user.has_perm('chaves.poder_ver_do_campus'):
            self.fields['chaves'].queryset = Chave.objects.filter(sala__predio__uo=get_uo(user))
        else:
            salas_permitidas = Sala.ativas.filter(avaliadores_de_agendamentos=user)
            self.fields['chaves'].queryset = Chave.objects.filter(sala__in=salas_permitidas.values_list('id', flat=True))


class PeriodoForm(forms.FormPlus):
    data_inicio = forms.DateFieldPlus(label='Data Inicial', required=True)
    data_termino = forms.DateFieldPlus(label='Data Final', required=True)
