from ckeditor.widgets import CKEditorWidget
from django.forms.models import inlineformset_factory
import uuid
from centralservicos.models import (
    CategoriaServico,
    GrupoServico,
    Servico,
    GrupoAtendimento,
    BaseConhecimento,
    Chamado,
    ChamadoAnexo,
    Comunicacao,
    AtendimentoAtribuicao,
    StatusChamado,
    CentroAtendimento,
    GestorAreaServico,
    AVALIACAO_CHOICES,
    Tag,
    Monitoramento,
    RespostaPadrao,
    GrupoInteressado,
)
from datetime import date, datetime
from comum.models import User, AreaAtuacao, Publico
from comum.utils import get_uo
from djtools import forms
from djtools.db import models
from djtools.forms.widgets import AutocompleteWidget
from rh.models import Setor, UnidadeOrganizacional


class ConfiguracaoForm(forms.FormPlus):
    servico = forms.ModelChoiceFieldPlus(Servico.objects, label='Serviço de Informar erro do SUAP', help_text='Informar erro do SUAP', required=False)

    centro_atendimento = forms.ModelChoiceFieldPlus(CentroAtendimento.objects, label='Centro de Atendimento de erros do SUAP', help_text='Sistêmico (Sistemas)', required=False)


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ['nome', 'area']


class GestorAreaServicoForm(forms.ModelForm):
    gestor = forms.ModelChoiceFieldPlus(
        queryset=User.objects.filter(is_active=True, pessoafisica__isnull=False),
        widget=AutocompleteWidget(search_fields=User.SEARCH_FIELDS),
        label='Gestor',
        help_text='Informe o nome do gestor desta área de serviço.',
    )

    class Meta:
        model = GestorAreaServico
        fields = ['gestor', 'area']


class CentroAtendimentoForm(forms.ModelForm):
    class Meta:
        model = CentroAtendimento
        exclude = ()


class CategoriaServicoForm(forms.ModelForm):
    class Meta:
        model = CategoriaServico
        exclude = ()


class GrupoServicoForm(forms.ModelForm):
    detalhamento = forms.CharField(label="Detalhamento", widget=forms.Textarea(attrs={'rows': '50', 'cols': '100'}))

    class Meta:
        model = GrupoServico
        exclude = ()


class ServicoForm(forms.ModelForm):
    publico_direcionado = forms.ModelMultipleChoiceField(
        label='Público',
        queryset=Publico.objects.all(),
        widget=forms.CheckboxSelectMultiple(),
        required=False,
        help_text='Caso deseje restringir este serviço a apenas alguns tipos de usuário, selecione um ou mais.',
    )

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

    class Meta:
        model = Servico
        exclude = ()

    class Media:
        js = ('/static/centralservicos/js/ServicoForm.js',)


class GrupoAtendimentoForm(forms.ModelForm):

    class Meta:
        model = GrupoAtendimento
        exclude = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        usuarios_ativos = User.objects.filter(is_active=True, pessoafisica__isnull=False)
        self.fields['campus'].queryset = UnidadeOrganizacional.objects.suap()
        self.fields['responsaveis'].queryset = usuarios_ativos
        self.fields['atendentes'].queryset = usuarios_ativos

    def clean_grupo_atendimento_superior(self):
        """
            Verifica se informou o Grupo de Atendimento Superior
            Em caso positivo, verifica se o id do Grupo de Atendimento atual
            é igual ao id do Grupo de Atendimento Superior
        """
        if self.cleaned_data['grupo_atendimento_superior'] and self.instance.id == self.cleaned_data['grupo_atendimento_superior'].id:
            raise forms.ValidationError('O Grupo de Atendimento Superior não pode ser o próprio Grupo de Atendimento.')

        return self.cleaned_data['grupo_atendimento_superior']

    def clean(self):
        super().clean()

        if not self.cleaned_data.get('grupo_atendimento_superior'):
            centro_atendimento = self.cleaned_data.get('centro_atendimento')
            if not centro_atendimento:
                raise forms.ValidationError('Escolha um centro de atendimento.')
            qs = GrupoAtendimento.objects.filter(grupo_atendimento_superior__isnull=True, centro_atendimento__area=centro_atendimento.area).exclude(id=self.instance.id)
            if qs.exists():
                raise forms.ValidationError('Não é possível mais um grupo Raiz.')


class BaseConhecimentoForm(forms.ModelFormPlus):
    solucao = forms.CharField(label='Solução', widget=CKEditorWidget(config_name='basic_suap'))

    class Meta:
        model = BaseConhecimento
        fields = ['area', 'titulo', 'resumo', 'solucao', 'ativo', 'tags', 'visibilidade', 'grupos_atendimento', 'servicos']

    class Media:
        js = ('/static/centralservicos/js/ckeditor_toolbar.js', '/static/centralservicos/js/BaseConhecimentoForm.js')

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)

    def clean_grupos_atendimento(self):
        if (self.cleaned_data.get('visibilidade') != BaseConhecimento.VISIBILIDADE_SIGILOSA) and (self.cleaned_data.get('grupos_atendimento')):
            return ''
        else:
            return self.cleaned_data.get('grupos_atendimento')

    def clean(self):
        if not self.request.user.has_perm('centralservicos.add_public_baseconhecimento') and self.instance.visibilidade == BaseConhecimento.VISIBILIDADE_PUBLICA:
            raise forms.ValidationError('Você não tem permissão para adicionar uma base de conhecimento com visibilidade pública.')
        return self.cleaned_data

    def save(self, *args, **kwargs):
        if self.instance.pk:
            atual = BaseConhecimento.objects.get(pk=self.instance.pk)
            if (self.instance.resumo != atual.resumo) or (self.instance.solucao != atual.solucao):
                self.instance.atualizado_em = datetime.now()
                self.instance.atualizado_por = self.request.user
        else:
            self.instance.atualizado_por = self.request.user
        return super().save(*args, **kwargs)


def ChamadoFormFactory(request, chamado=None, servico=None):
    if chamado:
        servico = chamado.servico

    class ChamadoForm(forms.ModelForm):
        interessado = forms.ModelChoiceFieldPlus(queryset=User.objects.filter(pessoafisica__isnull=False), widget=AutocompleteWidget(url='/centralservicos/ac_interessado/'), label='Interessado')
        requisitante = forms.ModelChoiceFieldPlus(
            queryset=User.objects.filter(is_active=True, pessoafisica__isnull=False), widget=AutocompleteWidget(search_fields=User.SEARCH_FIELDS), label='Requisitante'
        )
        outros_interessados = forms.MultipleModelChoiceFieldPlus(
            queryset=User.objects.filter(is_active=True, pessoafisica__isnull=False),
            widget=AutocompleteWidget(url='/centralservicos/ac_interessado/', multiple=True),
            label='Outros Interessados',
            help_text='Vincule outros usuários a este chamado. Eles poderão acompanhar as alterações ' 'e comentários deste chamado.',
            required=False,
        )
        uo = forms.CharField(label='Campus', widget=forms.Select(), required=True)
        centro_atendimento = forms.CharField(
            label='Centro de Atendimento', required=True, widget=forms.RadioSelect(), help_text='Selecione o Centro de Atendimento que mais se adequa ao seu problema.'
        )

        enviar_copia_email = forms.BooleanField(widget=forms.CheckboxInput, required=False, label='Enviar cópia de abertura deste chamado para os interessados?')

        class Meta:
            model = Chamado
            fields = [
                'descricao',
                'numero_patrimonio',
                'interessado',
                'requisitante',
                'telefone_adicional',
                'uo',
                'centro_atendimento',
                'meio_abertura',
                'outros_interessados',
                'enviar_copia_email',
            ]

        class Media:
            js = ('/static/centralservicos/js/get_centros_atendimento_por_campus.js',)

        def __init__(self, *args, **kwargs):
            """
                Se o usuário logado não for um Atendente, os campos Meio de Abertura e
                Requisitante não devem aparecer
            """
            super().__init__(*args, **kwargs)
            self.fields['uo'].widget.attrs['data-servico_id'] = servico.id

            self.fields['requisitante'].required = False
            if not request.user.has_perm('centralservicos.change_chamado'):
                del self.fields['meio_abertura']
                del self.fields['requisitante']
            if not request.user.has_perm('centralservicos.change_chamado') and servico.permite_abertura_terceiros is False:
                del self.fields['interessado']

            if request.user.has_perm('centralservicos.change_chamado') and servico.permite_abertura_terceiros is False:
                del self.fields['requisitante']

            if servico.requer_numero_patrimonio is False:
                del self.fields['numero_patrimonio']
            if servico.permite_telefone_adicional is False:
                del self.fields['telefone_adicional']

        def clean(self):
            if not self.errors:
                if self.cleaned_data.get('uo'):
                    uo = self.cleaned_data['uo']
                    campus = UnidadeOrganizacional.objects.get(pk=uo)
                    grupo = None
                    centroatendimento = None
                    if self.cleaned_data.get('centro_atendimento'):
                        centroatendimento = self.cleaned_data.get('centro_atendimento')
                        grupo = GrupoAtendimento.get_grupo_primeiro_nivel(uo, centroatendimento)
                    if not grupo:
                        mensagem = f'Nenhum grupo de atendimento foi cadastrado para o campus ({campus}) do servidor Interessado, no centro de atendimento ({centroatendimento}).'
                        raise forms.ValidationError(mensagem)
            return self.cleaned_data

        def clean_centro_atendimento(self):
            data = self.cleaned_data.get('centro_atendimento')
            if data:
                data = CentroAtendimento.objects.get(pk=data)
            else:
                raise forms.ValidationError('É necessário informar um centro de atendimento.')
            return data

        def clean_requisitante(self):
            """
                Se possui interessado e não possui requisitante, o interessado é o próprio requisitante
            """
            if not self.errors:
                if self.cleaned_data['interessado'] and not self.cleaned_data['requisitante']:
                    return self.cleaned_data['interessado']
                else:
                    return self.cleaned_data['requisitante']
            else:
                raise forms.ValidationError('Verifique o preenchimento de campos obrigatórios.')

    ChamadoForm.base_fields['meio_abertura'].initial = Chamado.MEIO_ABERTURA_WEB

    if not request.user.has_perm('centralservicos.change_chamado'):
        ChamadoForm.base_fields['interessado'].initial = request.user

    if servico.requer_numero_patrimonio:
        ChamadoForm.base_fields['numero_patrimonio'].required = True

    return ChamadoForm


ChamadoAnexoFormset = inlineformset_factory(Chamado, ChamadoAnexo, extra=3, exclude=['chamado', 'anexado_em', 'anexado_por'], can_delete=False)


class ChamadoAnexoForm(forms.ModelForm):
    class Meta:
        model = ChamadoAnexo
        fields = ['descricao', 'anexo']


def ComunicacaoFormFactory(request, chamado, operacao=None):
    class ComunicacaoForm(forms.ModelFormPlus):
        atribuido_para = forms.ModelChoiceField(required=False, queryset=User.objects.none())
        texto = forms.CharField(label='Texto', widget=forms.Textarea(attrs={'rows': '50', 'cols': '100'}))
        usuarios_citados = forms.MultipleModelChoiceFieldPlus(
            label='Citar Outros Atendentes',
            required=False,
            queryset=User.objects.none(),
            help_text='Caso deseje enviar uma notificação com o texto deste comunicado a outros atendentes, especifique-os aqui. Atendentes sem emails não serão listados.',
        )
        bases_conhecimento = forms.MultipleModelChoiceFieldPlus(
            label='Sugerir Artigos da Base de Conhecimentos',
            required=False,
            widget=forms.CheckboxSelectMultiple(),
            queryset=chamado.servico.get_bases_conhecimento_faq(),
            help_text='Caso deseje sugerir algum Artigo da Base de Conhecimentos para o(s) interessado(s) deste chamado, especifique-as.',
        )

        class Meta:
            model = Comunicacao
            fields = ['texto', 'usuarios_citados', 'bases_conhecimento']

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            atendentes = list(chamado.get_atendentes_equipe_atendimento().values_list('id', flat=True))
            responsaveis = list(chamado.get_responsaveis_equipe_atendimento().values_list('id', flat=True))
            ids = atendentes + responsaveis
            if chamado.get_atendente_do_chamado():
                self.fields['usuarios_citados'].queryset = User.objects.filter(id__in=ids).exclude(id=chamado.get_atendente_do_chamado().id).exclude(email='')
            else:
                self.fields['usuarios_citados'].queryset = User.objects.filter(id__in=ids).exclude(email='')

            atribuicao = chamado.get_atendimento_atribuicao_atual()
            if operacao is not None:
                del self.fields['bases_conhecimento']
            if operacao == 'escalar':
                if not (request.user.is_superuser or atribuicao.grupo_atendimento.grupo_atendimento_superior.responsaveis.filter(pk=request.user.pk).exists()):
                    del self.fields['atribuido_para']
                else:
                    self.fields['atribuido_para'].queryset = atribuicao.grupo_atendimento.grupo_atendimento_superior.atendentes
            elif operacao == 'retornar':
                if not (request.user.is_superuser or (atribuicao.grupo_atendimento.get_grupo_antendimento_inferior(chamado).responsaveis.filter(pk=request.user.pk).exists())):
                    del self.fields['atribuido_para']
                else:
                    self.fields['atribuido_para'].queryset = atribuicao.grupo_atendimento.get_grupo_antendimento_inferior(chamado).atendentes

    return ComunicacaoForm


def AtendimentoAtribuicaoFormFactory(request, grupo_atendimento):
    class AtendimentoAtribuicaoForm(forms.ModelForm):
        atribuido_para = forms.ModelChoiceField(queryset=grupo_atendimento.atendentes.exclude(id__in=[request.user.id]))

        class Meta:
            model = AtendimentoAtribuicao
            fields = ['atribuido_para']

    return AtendimentoAtribuicaoForm


def BuscarChamadoUsuarioFormFactory(request):
    fields = {
        'chamado_id': forms.IntegerFieldPlus(required=False, label='ID'),
        'area': forms.ModelChoiceFieldPlus2(AreaAtuacao.objects, label='Área de Serviços', required=False),
        'data_inicial': forms.DateFieldPlus(required=False, label='Data Inicial'),
        'data_final': forms.DateFieldPlus(required=False, label='Data Final'),
        'tipo_usuario': forms.ChoiceField(label='Considerar apenas quando eu for:', choices=Chamado.TIPO_USUARIO_CHOICES, required=False),
    }

    fieldsets = ((None, {'fields': ('chamado_id', 'area', ('data_inicial', 'data_final'), 'tipo_usuario')}),)

    def clean(self):
        msg = {'erro': 'O campo data inicial não pode ser maior que data final.'}
        if not self.errors:
            if self.cleaned_data['data_inicial'] and self.cleaned_data['data_final']:
                if self.cleaned_data['data_inicial'] > self.cleaned_data['data_final']:
                    self.errors['data_inicial'] = [msg['erro']]
        return self.cleaned_data

    return type('BuscarChamadoUsuarioForm', (forms.BaseForm,), {'base_fields': fields, 'clean': clean, 'fieldsets': fieldsets, 'METHOD': 'GET'})


def BuscarChamadoSuporteFormFactory(request, area=None):
    """
    Cria uma classe para o formulário de busca de chamados para Equipe do Suporte
    """
    ORDENAR_POR_SITUACAO = 'status'
    ORDENAR_POR_SERVICO = 'servico__nome'
    ORDENAR_POR_ABERTO_EM = 'aberto_em'
    ORDENAR_POR_ABERTO_POR = 'aberto_por__pessoafisica__nome'
    ORDENAR_POR_INTERESSADO = 'interessado__pessoafisica__nome'
    ORDENAR_POR_DATA_LIMITE_ATENDIMENTO = 'data_limite_atendimento'

    ORDENACAO_CRESCENTE = ''
    ORDENACAO_DECRESCENTE = '-'

    ORDERNAR_POR_CHOICES = [
        [ORDENAR_POR_DATA_LIMITE_ATENDIMENTO, 'Data Limite do Atendimento'],
        [ORDENAR_POR_ABERTO_EM, 'Data Abertura'],
        [ORDENAR_POR_SITUACAO, 'Situação'],
        [ORDENAR_POR_SERVICO, 'Serviço'],
        [ORDENAR_POR_ABERTO_POR, 'Aberto Por'],
        [ORDENAR_POR_INTERESSADO, 'Interessado'],
    ]
    TIPO_ORDENACAO_CHOICES = [[ORDENACAO_CRESCENTE, 'Crescente'], [ORDENACAO_DECRESCENTE, 'Decrescente']]

    fields = {
        'chamado_id': forms.IntegerFieldPlus(required=False, label='ID'),
        'data_inicial': forms.DateFieldPlus(required=False, label='Data Inicial'),
        'data_final': forms.DateFieldPlus(required=False, label='Data Final'),
        'tipo': forms.ChoiceField(choices=[('', '---------')] + Servico.TIPO_CHOICES, required=False, label='Tipo'),
        'status': forms.MultipleChoiceField(choices=StatusChamado.STATUS, widget=forms.CheckboxSelectMultiple, required=False, label='Situação'),
        'todos_status': forms.BooleanField(required=False, label='Todas as Situações'),
        'nota_avaliacao': forms.ChoiceField(choices=[('', '---------')] + AVALIACAO_CHOICES, required=False, label='Nota da Avaliação'),
        'uo': forms.MultipleModelChoiceFieldPlus(
            UnidadeOrganizacional.objects.suap().filter(pk__in=GrupoAtendimento.meus_grupos(request.user).values_list('campus', flat=True)),
            required=False,
            label='Unidade Organizacional',
        ),

        'area': forms.MultipleModelChoiceFieldPlus(GrupoAtendimento.areas_vinculadas_ao_meu_centro_atendimento(request.user), required=False, label='Área',),
        'grupo_atendimento': forms.MultipleModelChoiceFieldPlus(GrupoAtendimento.meus_grupos(request.user, area), required=False, label='Grupo de Atendimento'),
        'atribuicoes': forms.ChoiceField(label='Atribuições', widget=forms.RadioSelect(), choices=[('', 'Todas')] + Chamado.ATRIBUICOES_CHOICES, required=False),
        'texto': forms.CharField(
            label='Buscar por', required=False, help_text='Conteúdo a ser pesquisado nas descrições, número de patrimônio, comentários e ' 'notas internas dos chamados'
        ),
        'considerar_escalados': forms.BooleanField(required=False, label='Considerar chamados escalados/retornados'),
        'servico': forms.ModelChoiceFieldPlus(Servico.objects.filter(ativo=True), required=False, label='Serviço', widget=AutocompleteWidget(search_fields=Servico.SEARCH_FIELDS)),
        'grupo_servico': forms.ModelChoiceFieldPlus(GrupoServico.objects.all(), required=False, label='Grupo de Serviço'),
        'interessado': forms.ModelChoiceFieldPlus(
            User.objects.filter(is_active=True, pessoafisica__isnull=False), required=False, label='Interessado', widget=AutocompleteWidget(search_fields=User.SEARCH_FIELDS)
        ),
        'aberto_por': forms.ModelChoiceFieldPlus(
            User.objects.filter(is_active=True, pessoafisica__isnull=False), required=False, label='Aberto Por', widget=AutocompleteWidget(search_fields=User.SEARCH_FIELDS)
        ),
        'atendente': forms.ModelChoiceFieldPlus(
            User.objects.filter(models.Q(atendentes_set__isnull=False) | models.Q(responsaveis_set__isnull=False)).distinct(),
            required=False,
            label='Atendente',
            widget=AutocompleteWidget(search_fields=User.SEARCH_FIELDS),
        ),
        'ordenar_por': forms.ChoiceField(choices=ORDERNAR_POR_CHOICES, initial=ORDENAR_POR_DATA_LIMITE_ATENDIMENTO, required=False),
        'tipo_ordenacao': forms.ChoiceField(widget=forms.RadioSelect, choices=TIPO_ORDENACAO_CHOICES, initial=ORDENACAO_CRESCENTE, required=False),
        'sla_estourado': forms.BooleanField(required=False, label='Somente com SLA estourado'),
    }

    fieldsets = (
        (
            None,
            {
                'fields': (
                    ('chamado_id', 'texto'),
                    ('data_inicial', 'data_final'),
                    'uo',
                    ('area', 'grupo_atendimento'),
                    ('grupo_servico', 'servico'),
                    ('status', 'todos_status', 'considerar_escalados'),
                    'atribuicoes',
                    'atendente',
                    ('interessado', 'aberto_por'),
                    ('tipo', 'nota_avaliacao'),
                    ('ordenar_por', 'tipo_ordenacao'),
                    ('sla_estourado'),
                )
            },
        ),
    )

    def clean(self):
        msg = {'erro': 'O campo Data Inicial não pode ser maior que Data Final.'}
        if not self.errors:
            if self.cleaned_data['data_inicial'] and self.cleaned_data['data_final']:
                if self.cleaned_data['data_inicial'] > self.cleaned_data['data_final']:
                    self.errors['data_inicial'] = [msg['erro']]
        return self.cleaned_data

    return type('BuscarChamadoSuporteForm', (forms.BaseForm,), {'base_fields': fields, 'clean': clean, 'fieldsets': fieldsets, 'METHOD': 'GET'})


def BuscarServicoFormFactory(user, area, servico_interno=None):
    def get_servicos():
        if servico_interno:
            servicos = Servico.objects.filter(ativo=True, interno=servico_interno, grupo_servico__categorias__area=area).distinct()
        else:
            servicos = Servico.objects.filter(ativo=True, grupo_servico__categorias__area=area).distinct()
        ids = [s.id for s in servicos if s.pode_acessar_servico(user)]
        return Servico.objects.filter(id__in=ids).distinct()

    fields = {
        'servico': forms.ModelChoiceFieldPlus(
            queryset=get_servicos(), widget=AutocompleteWidget(search_fields=Servico.SEARCH_FIELDS, submit_on_select=True), label='Qual serviço você precisa?', required=False
        )
    }

    fieldsets = ((None, {'fields': ('servico',)}),)

    return type('BuscarServicoFormForm', (forms.BaseForm,), {'base_fields': fields, 'fieldsets': fieldsets, 'METHOD': 'POST'})


def BuscarArtigoFormFactory(request, eh_atendente_desta_area=None, area=None):
    class BuscarArtigoForm(forms.FormPlus):
        METHOD = 'POST'
        if eh_atendente_desta_area and area:
            BaseConhecimento.objects.filter(area=area, ativo=True).order_by('-atualizado_em')[:5]
            baseconhecimento = forms.ModelChoiceFieldPlus(
                queryset=BaseConhecimento.objects.filter(area=area, ativo=True).distinct(),
                widget=AutocompleteWidget(search_fields=BaseConhecimento.SEARCH_FIELDS, submit_on_select=True),
                label='Buscar Artigo',
                required=False,
            )
        else:
            baseconhecimento = forms.ModelChoiceFieldPlus(
                queryset=BaseConhecimento.objects.filter(visibilidade=BaseConhecimento.VISIBILIDADE_PUBLICA, ativo=True).distinct(),
                widget=AutocompleteWidget(search_fields=BaseConhecimento.SEARCH_FIELDS, submit_on_select=True),
                label='Buscar Artigo',
                required=False,
            )

    return BuscarArtigoForm


def ReclassificarChamadoFormFactory(request, chamado=None, troca_area=None):
    class ReclassificarChamadoForm(forms.ModelFormPlus):
        consulta = Servico.objects.filter(ativo=True, area=chamado.servico.area).order_by('grupo_servico', 'nome')
        if troca_area == True:
            consulta = Servico.objects.filter(ativo=True).order_by('grupo_servico', 'nome')

        if chamado and chamado.servico.interno == False:
            servico = forms.ModelPopupChoiceField(queryset=consulta.filter(interno=False), label='Novo Serviço', initial=chamado.servico.id)
        else:
            servico = forms.ModelPopupChoiceField(queryset=consulta, label='Novo Serviço', initial=chamado.servico.id)
        uo = forms.CharField(label='Campus', widget=forms.Select(), required=True, initial=chamado.campus.id)
        centro_atendimento = forms.CharField(
            label='Centro de Atendimento',
            widget=forms.RadioSelect(),
            help_text='Selecione o Centro de Atendimento que mais se adequa ao seu problema',
            initial=chamado.get_atendimento_atribuicao_atual().grupo_atendimento.centro_atendimento.id,
        )
        justificativa = forms.CharField(label="Justificativa", widget=forms.Textarea(attrs={'rows': '50', 'cols': '100'}))

        class Meta:
            model = Chamado
            fields = ['servico', 'uo', 'centro_atendimento', 'justificativa']

        class Media:
            js = ('/static/centralservicos/js/get_centros_atendimento_por_campus.js',)

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields['uo'].widget.attrs['data-servico_id'] = chamado.servico.id
            self.fields['uo'].widget.attrs['data-chamado_id'] = chamado.id

        def clean(self):
            if not self.errors:
                if chamado.servico == self.cleaned_data.get('servico') and chamado.get_atendimento_atribuicao_atual().grupo_atendimento.centro_atendimento == self.cleaned_data.get(
                    'centro_atendimento'
                ):
                    raise forms.ValidationError(
                        'Nenhuma mudança foi identificada na reclassificação do chamado. Por favor, verifique se o serviço selecionado ou o centro de atendimento são diferentes do atual.'
                    )

                if self.cleaned_data.get('uo') and self.cleaned_data.get('centro_atendimento'):
                    campus = UnidadeOrganizacional.objects.suap().get(pk=self.cleaned_data.get('uo'))
                    centro_atendimento = CentroAtendimento.objects.get(pk=self.cleaned_data.get('centro_atendimento'))
                    grupo = GrupoAtendimento.get_grupo_primeiro_nivel(campus, centro_atendimento)
                    if not grupo:
                        raise forms.ValidationError(
                            'Nenhum grupo de atendimento foi cadastrado para o campus ({}) '
                            'do servidor Interessado, no centro de atendimento ({}).'.format(campus, centro_atendimento)
                        )
            return self.cleaned_data

    return ReclassificarChamadoForm


class FecharEAvaliarChamadoForm(forms.FormPlus):
    class Media:
        js = ('/static/centralservicos/js/stars.js',)

    METHOD = 'POST'
    nota_avaliacao = forms.ChoiceField(
        label='Nota para Atendimento do Chamado', widget=forms.RadioSelect(), choices=AVALIACAO_CHOICES, required=False, help_text='Avalie o atendimento deste chamado.'
    )
    comentario = forms.CharField(
        label='Comentário', widget=forms.Textarea(attrs={'rows': '50', 'cols': '100'}), required=False, help_text='Se desejar, faça um comentário sobre sua avaliação.'
    )


def GraficosFormFactory(request, data_inicio, data_termino):
    fields = {
        'inicio': forms.DateFieldPlus(label='Data de Início', required=True, initial=data_inicio),
        'termino': forms.DateFieldPlus(label='Data de Término', required=True, initial=data_termino),
        'uo': forms.ModelChoiceField(UnidadeOrganizacional.objects.uo().all(), required=False, label='Unidade Organizacional', initial=get_uo(request.user).pk),
        'grupo_atendimento': forms.ModelChoiceField(GrupoAtendimento.meus_grupos(request.user), required=False, label='Grupo de Atendimento'),
    }

    if GrupoAtendimento.areas_vinculadas_ao_meu_centro_atendimento(request.user).count() > 1:
        fields['area'] = forms.ModelChoiceField(GrupoAtendimento.areas_vinculadas_ao_meu_centro_atendimento(request.user), required=False, label='Área do Serviço')

    fieldsets = ((None, {'fields': ('area', 'inicio', 'termino', 'uo', 'grupo_atendimento')}),)

    return type('GraficosForm', (forms.BaseForm,), {'base_fields': fields, 'fieldsets': fieldsets, 'METHOD': 'GET'})


class AtendimentosPorAnoForm(forms.FormPlus):
    inicio = forms.IntegerFieldPlus(label='Ano de Início', required=True)
    termino = forms.IntegerFieldPlus(label='Ano de Término', required=True)
    area = forms.ModelChoiceField(GrupoAtendimento.objects, required=False, label='Área do Serviço')

    fieldsets = ((None, {'fields': ('area', 'inicio', 'termino', 'uo', 'grupo_atendimento')}),)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hoje = date.today()
        choices_anos = ((ano, ano) for ano in Chamado.objects.filter().values_list('aberto_em__year').distinct())
        self.fields['inicio'].choices = choices_anos
        self.fields['termino'].choices = choices_anos
        self.fields['inicio'].initial = hoje.year
        self.fields['termino'].initial = hoje.year
        self.fields['area'].queryset = GrupoAtendimento.areas_vinculadas_ao_meu_centro_atendimento(self.request.user)


def AtendentesFormFactory(request):
    fields = {
        'uo': forms.ModelChoiceField(UnidadeOrganizacional.objects.uo().all(), required=False, label='Unidade Organizacional'),
        'grupo_atendimento': forms.ModelChoiceField(GrupoAtendimento.meus_grupos(request.user), required=False, label='Grupo de Atendimento'),
        'setor': forms.ModelChoiceFieldPlus(Setor.objects.filter(excluido=False), required=False, label='Setor'),
    }

    if GrupoAtendimento.areas_vinculadas_ao_meu_centro_atendimento(request.user).count() > 1:
        fields['area'] = forms.ModelChoiceField(GrupoAtendimento.areas_vinculadas_ao_meu_centro_atendimento(request.user), required=False, label='Área do Serviço')

    fieldsets = ((None, {'fields': ('area', 'grupo_atendimento', 'setor', 'uo')}),)

    return type('AtendentesForm', (forms.BaseForm,), {'base_fields': fields, 'fieldsets': fieldsets, 'METHOD': 'GET'})


def AlterarStatusChamadoFormFactory(request, servico, grupo_atendimento):
    class AlterarStatusChamadoForm(forms.ModelForm):
        """
            O objetivo é listar as bases de conhecimento disponíveis ao serviço,
            apenas no grupo de atendimento do usuário
        """

        bases_conhecimento = forms.ModelMultipleChoiceField(
            label='Bases de Conhecimento',
            queryset=servico.get_bases_de_conhecimento_disponiveis_para_resolucao(grupo_atendimento),
            widget=forms.CheckboxSelectMultiple(),
            help_text='Selecione uma ou mais bases de conhecimento',
        )
        observacao = forms.CharField(
            label="Comentário", help_text='Este comentário será adicionado à Linha do Tempo deste Chamado', widget=forms.Textarea(attrs={'rows': '50', 'cols': '100'})
        )

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            if not grupo_atendimento:
                del self.fields['bases_conhecimento']

        class Meta:
            model = Chamado
            fields = ['bases_conhecimento']

        class Media:
            js = ('/static/centralservicos/js/AlterarStatusChamadoFormFactory.js',)

    return AlterarStatusChamadoForm


def AdicionarOutrosInteressadosFormFactory(request, chamado):
    class AdicionarOutrosInteressadosForm(forms.Form):
        METHOD = 'POST'
        outros_interessados = forms.MultipleModelChoiceFieldPlus(
            queryset=User.objects.filter(is_active=True, pessoafisica__isnull=False).exclude(pk__in=chamado.outros_interessados.all().values_list('pk', flat=True)),
            label='Outros Interessados',
            help_text='Vincule outros usuários a este chamado. Eles poderão acompanhar as alterações e ' 'comentários deste chamado.',
            required=True,
        )

    return AdicionarOutrosInteressadosForm


def AdicionarTagsAoChamadoFormFactory(request, chamado):
    class AdicionarTagsAoChamadoForm(forms.Form):
        METHOD = 'POST'
        tags = forms.ModelMultipleChoiceField(
            queryset=Tag.objects.exclude(id__in=chamado.tags.all()).filter(area__in=GrupoAtendimento.areas_vinculadas_ao_meu_centro_atendimento(request.user)),
            widget=forms.CheckboxSelectMultiple(),
            label='Tags',
            help_text='Vincule tags a este chamado para facilitar a identificação do mesmo.',
            required=True,
        )

    return AdicionarTagsAoChamadoForm


class MarcarParaCorrecaoForm(forms.FormPlus):
    comentario = forms.CharField(
        label='Comentário',
        required=True,
        help_text='Informe o motivo da necessidade de correção da base de conhecimento.',
        widget=forms.Textarea(attrs={'rows': '50', 'cols': '100'}),
    )


class MonitoramentoForm(forms.ModelFormPlus):
    class Meta:
        model = Monitoramento
        fields = ['titulo', 'grupos', 'organizar_por_tipo']

    def save(self, *args, **kwargs):
        if not self.instance.pk:
            self.instance.token = uuid.uuid4().hex[:32].upper()
            self.instance.cadastrado_por = self.request.user
        return super().save(*args, **kwargs)


class RespostaPadraoForm(forms.ModelFormPlus):
    class Meta:
        model = RespostaPadrao
        fields = ['texto']


class GrupoInteressadoForm(forms.ModelForm):
    grupo_atendimento = forms.ModelChoiceFieldPlus(GrupoAtendimento.objects, widget=forms.Select(), label='Grupo de Atendimento')
    interessados = forms.MultipleModelChoiceFieldPlus(
        queryset=User.objects.filter(is_active=True, pessoafisica__isnull=False), label='Interessados'
    )

    class Meta:
        model = GrupoInteressado
        fields = ['titulo', 'grupo_atendimento', 'interessados']

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.fields['grupo_atendimento'].queryset = GrupoAtendimento.meus_grupos(self.request.user)


def AdicionarGrupoInteressadosFormFactory(request, chamado):
    class AdicionarGrupoInteressadosForm(forms.Form):
        METHOD = 'POST'
        grupos_interessados = forms.ModelMultipleChoiceField(
            queryset=GrupoInteressado.objects.filter(grupo_atendimento=chamado.get_atendimento_atribuicao_atual().grupo_atendimento),
            widget=forms.CheckboxSelectMultiple(),
            label='Grupos de Interessado',
            required=True,
        )

    return AdicionarGrupoInteressadosForm
