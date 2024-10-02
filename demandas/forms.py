import hashlib
from datetime import date, datetime

import time
from ckeditor.fields import RichTextFormField
from django.contrib import auth
from django.contrib.auth.models import Group
from django.forms import ValidationError
from django.utils.safestring import mark_safe

from comum.models import User, UsuarioGrupo, Configuracao
from demandas.models import AmbienteHomologacao, AnalistaDesenvolvedor
from demandas.models import Anexos, Atualizacao, Demanda, DoD, Especificacao, NotaInterna, Situacao, Tag, \
    AreaAtuacaoDemanda, HistoricoSituacao, Notificar
from demandas.models import SugestaoMelhoria
from djtools import forms
from djtools.forms import ModelFormPlus
from djtools.forms.fields import DateFieldPlus
from djtools.forms.widgets import AutocompleteWidget
from djtools.templatetags.filters import in_group
from djtools.utils import gitlab


class ConfiguracaoForm(forms.FormPlus):
    gitlab_url = forms.CharFieldPlus(label='URL do gitlab', required=False, initial='https://gitlab.ifrn.edu.br')
    gitlab_token = forms.CharFieldPlus(label='Token do gitlab', required=False)
    gitlab_suap_id = forms.CharFieldPlus(label='ID do projeto SUAP', required=False, initial='8')
    gitlab_api_version = forms.CharFieldPlus(label='Versão da API do Gitlab', required=False, initial='4')
    dominio_suapdevs = forms.CharFieldPlus(label='Domínio do Ambiente de Homologação', required=False, initial='suapdevs.ifrn.edu.br')
    bancos_suapdevs = forms.CharFieldPlus(label='Bancos de Template para Ambientes de Homologação', required=False, initial='behave suap_mascarado_pequeno')


class ListarDemandaForm(forms.ModelForm):
    class Meta:
        model = Demanda
        exclude = ()


class ConfirmarComSenhaForm(forms.Form):
    senha = forms.CharField(label='Senha para confirmar', widget=forms.PasswordInput)
    confirmar = forms.BooleanField(label='Confirma a operação')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()

        if 'confirmar' in cleaned_data and cleaned_data['confirmar']:
            if not auth.authenticate(username=self.request.user.username, password=cleaned_data['senha']):
                raise forms.ValidationError('A senha não confere com a do usuário logado.')

        return cleaned_data


class AreaAtuacaoDemandaForm(ModelFormPlus):
    demandantes = forms.MultipleModelChoiceFieldPlus(
        label='Demandantes',
        queryset=User.objects.filter(is_active=True),
        help_text='Vincule demandantes a essa Área de Atuação',
        required=False,
    )
    demandante_responsavel = forms.ModelChoiceFieldPlus(
        label='Demandante Responsável', queryset=User.objects.filter(is_active=True), help_text='Vincule um Demandante Responsável por essa Área de Atuação', required=True
    )
    tags_relacionadas = forms.MultipleModelChoiceFieldPlus(
        label='Tags',
        queryset=Tag.objects,
        help_text='Vincule tags a essa Área de Atuação',
        required=False,
    )

    class Meta:
        model = AreaAtuacaoDemanda
        fields = ('area', 'demandante_responsavel', 'demandantes', 'tags_relacionadas', 'recebe_sugestoes')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not in_group(self.request.user, 'Coordenador de TI sistêmico'):
            self.fields['area'].widget = forms.HiddenInput()
            self.fields['demandante_responsavel'].widget = forms.HiddenInput()

    def clean(self, *args, **kwargs):
        recebe_sugestoes = self.cleaned_data.get('recebe_sugestoes')

        if recebe_sugestoes:
            tags_relacionadas = self.cleaned_data.get('tags_relacionadas')

            if tags_relacionadas:
                tags_ja_selecionadas = {}  # {tag: [area, area, ...]}

                for tag in tags_relacionadas:
                    tags_ja_selecionadas.update({tag: []})

                    for area in AreaAtuacaoDemanda.areas_recebem_sugestoes().exclude(id=self.instance.id)\
                            .filter(tags_relacionadas=tag):
                        tags_ja_selecionadas[tag].append(area)

                    if not len(tags_ja_selecionadas[tag]):
                        del tags_ja_selecionadas[tag]

                if tags_ja_selecionadas:
                    self.add_error(None, 'Área de Atuação recebe sugestões de melhoria.')
                    self.add_error('tags_relacionadas',
                                   ValidationError('Tags já selecionadas em outras Áreas de Atuação: {}'.format(
                                       ', '.join(['{} ({})'.format(tag, ', '.join('{}'.format(area) for area in
                                                                                  tags_ja_selecionadas[tag]))
                                                  for tag in tags_ja_selecionadas.keys()])))
                                   )
            else:
                self.add_error(None, 'Área de Atuação recebe sugestões de melhoria.')
                self.add_error('tags_relacionadas',
                               ValidationError('Informe pelo menos uma Tag para ativar o recebimento de sugestões '
                                               'de melhorias.'))

        return self.cleaned_data


class DemandaForm(ModelFormPlus):
    def save(self, *args, **kwargs):
        insert = not self.instance.pk
        notificar_alteracao = False

        atualizar_prioridades = False

        if insert:
            self.instance.data_atualizacao = date.today()
            atualizar_prioridades = True
        else:
            demanda = Demanda.objects.get(pk=self.instance.pk)

            if demanda.descricao != self.instance.descricao:
                notificar_alteracao = True

            # Se a área de atuação da demanda mudar, a lista de prioridades deve ser atualizada após o Save da demanda
            if demanda.area != self.instance.area:
                demanda_anterior_area = demanda.area
                self.instance.prioridade = None
                atualizar_prioridades = True
            if self.cleaned_data.get('desenvolvedores'):
                novos_desenvolvedores = set(self.cleaned_data.get('desenvolvedores')) - set(self.instance.desenvolvedores.all())
                Notificar.desenvolvedores_vinculados_a_demanda(self.instance, novos_desenvolvedores, self.request.user)
            if self.cleaned_data.get('analistas'):
                novos_analistas = set(self.cleaned_data.get('analistas')) - set(self.instance.analistas.all())
                Notificar.analistas_vinculados_a_demanda(self.instance, novos_analistas, self.request.user)

        users = self.cleaned_data.get('interessados').all() | self.cleaned_data.get('observadores').all()
        group = Group.objects.get(name='Visualizador de Demandas')
        for user in users.distinct():
            if not UsuarioGrupo.objects.filter(user=user, group=group).exists():
                UsuarioGrupo.objects.get_or_create(group=group, user=user)

        retorno = super().save(commit=True)
        if insert:
            HistoricoSituacao.objects.create(demanda=self.instance, usuario=self.request.user, situacao=self.instance.situacao)
        if atualizar_prioridades:
            if not insert and demanda_anterior_area:
                Demanda.atualizar_prioridades(demanda_anterior_area, self.request.user)
            Demanda.atualizar_prioridades(self.instance.area, self.request.user)
            retorno = Demanda.objects.get(pk=retorno.pk)

        if notificar_alteracao:
            Notificar.alteracao_demanda(self.instance)

        return retorno

    def save_m2m(self):
        pass

    def clean(self, *args, **kwargs):
        privada = self.cleaned_data.get('privada')
        observadores = self.cleaned_data.get('observadores')
        interessados = self.cleaned_data.get('interessados')
        if privada and (observadores or interessados):
            if observadores:
                self.add_error('observadores', 'Demandas privadas não podem ter observadores.')
            if interessados:
                self.add_error('interessados', 'Demandas privadas não podem ter interessados.')

        return self.cleaned_data


class DemandaAddForm(DemandaForm):
    demandantes = forms.MultipleModelChoiceFieldPlus(
        label='Demandantes',
        queryset=User.objects.filter(is_active=True),
        help_text='Vincule demandantes a esta demanda.',
        required=False,
    )
    interessados = forms.MultipleModelChoiceFieldPlus(
        queryset=User.objects.filter(is_active=True),
        label='Interessados',
        help_text='Vincule outros usuários a esta demanda. Eles poderão acompanhar as alterações e comentários desta demanda.',
        required=False,
    )
    observadores = forms.MultipleModelChoiceFieldPlus(
        queryset=User.objects.filter(is_active=True),
        label='Observadores',
        help_text='Vincule outros usuários a esta demanda. Eles poderão acompanhar as alterações desta demanda.',
        required=False,
    )

    class Meta:
        model = Demanda
        fields = ('area', 'titulo', 'descricao', 'prazo_legal', 'privada', 'demandantes', 'interessados', 'observadores', 'consolidacao_sempre_visivel')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['demandantes'].queryset = User.objects.filter(groups=Group.objects.get(name='Demandante'))
        area_qs = AreaAtuacaoDemanda.objects.filter(demandantes=self.request.user) | AreaAtuacaoDemanda.objects.filter(demandante_responsavel=self.request.user)
        if area_qs.exists():
            self.fields['area'].queryset = area_qs.distinct()
        eh_analista = in_group(self.request.user, 'Analista')
        if not eh_analista and 'consolidacao_sempre_visivel' in self.fields:
            del self.fields['consolidacao_sempre_visivel']


class DemandaChangeForm(DemandaForm):
    demandantes = forms.MultipleModelChoiceFieldPlus(
        label='Demandantes', queryset=User.objects, help_text='Vincule demandantes a esta demanda.', required=False
    )
    interessados = forms.MultipleModelChoiceFieldPlus(
        label='Interessados',
        queryset=User.objects,
        help_text='Vincule outros usuários a esta demanda. Eles poderão acompanhar as alterações e comentários desta demanda.',
        required=False,
    )
    observadores = forms.MultipleModelChoiceFieldPlus(
        queryset=User.objects.filter(is_active=True),
        label='Observadores',
        help_text='Vincule outros usuários a esta demanda. Eles poderão acompanhar as alterações desta demanda.',
        required=False,
    )
    desenvolvedores = forms.MultipleModelChoiceFieldPlus(
        label='Desenvolvedores',
        queryset=User.objects,
        help_text='Vincule usuários desenvolvedores desta demanda.',
        required=False,
    )
    analistas = forms.MultipleModelChoiceFieldPlus(
        label='Analistas', queryset=User.objects, help_text='Vincule usuários analistas desta demanda.', required=False
    )
    tags = forms.MultipleModelChoiceFieldPlus(
        label='Tags', queryset=Tag.objects, help_text='Vincule tags a esta demanda.', required=False
    )

    class Meta:
        model = Demanda
        exclude = ('aberto_em', 'situacao', 'especificacao_tecnica')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['demandantes'].queryset = User.objects.filter(groups=Group.objects.get(name='Demandante'))
        self.fields['interessados'].queryset = User.objects.filter(is_active=True)
        self.fields['desenvolvedores'].queryset = User.objects.filter(groups=Group.objects.get(name='Desenvolvedor'))
        self.fields['analistas'].queryset = User.objects.filter(groups=Group.objects.get(name='Analista'))
        if 'id_repositorio' in self.fields:
            self.fields['id_repositorio'].required = False
        eh_analista = in_group(self.request.user, 'Analista')
        if not eh_analista and 'consolidacao_sempre_visivel' in self.fields:
            del self.fields['consolidacao_sempre_visivel']

    def clean_demandantes(self):
        data = self.cleaned_data['demandantes']
        if not data:
            raise forms.ValidationError('A demanda deve ter pelo menos um demandante.')
        return data


class DoDForm(forms.ModelForm):
    descricao = forms.CharFieldPlus(label='Descrição', required=True, help_text='Forneça uma descrição sucinta da demanda.')
    detalhamento = forms.CharFieldPlus(label='Detalhamento', required=False, widget=forms.Textarea(), help_text='Forneça uma descrição detalhada das mudanças/funcionalidades implementadas nesta demanda')

    class Meta:
        model = DoD
        fields = ('descricao', 'detalhamento', 'envolvidos')


class EspecificacaoForm(forms.ModelForm):
    atividades = RichTextFormField(label='Atividade(s)', config_name='basic_suap')

    class Meta:
        model = Especificacao
        fields = ('nome', 'atividades', 'ordem')

    def __init__(self, *args, **kwargs):
        self.dod = kwargs.pop('dod')

        super().__init__(*args, **kwargs)

        if self.instance.dod_id is None:
            self.instance.dod = self.dod

    def save(self, commit=True):
        if commit:
            save = super().save()
            if save:
                Especificacao.atualizar_ordens(self.dod)
            return save


class EspecificacaoTecnicaForm(forms.ModelForm):
    especificacao_tecnica = RichTextFormField(label='Especificação Técnica', config_name='basic_suap')

    class Meta:
        model = Demanda
        fields = ('especificacao_tecnica',)


def SituacaoAlterarFormFactory(situacao, url_validacao, senha_homologacao, desenvolvedores_demanda, analistas_demanda):
    hoje = date.today()

    situacao_form_factory = 'default'

    comentario = forms.CharField(label='Comentário', required=False, widget=forms.Textarea(attrs={'rows': '50', 'cols': '100'}))
    data_conclusao = DateFieldPlus(label='Conclusão', required=True, help_text='Informe a Data de Conclusão da etapa anterior', initial=hoje)
    data_previsao = DateFieldPlus(label='Previsão', required=True, help_text='Informe a Data de Previsão para conclusão desta etapa')
    url_validacao = forms.CharFieldPlus(label='URL para Ambiente de Homologação', required=False, initial=url_validacao)
    senha_homologacao = forms.CharFieldPlus(label='Senha para Ambiente de Homologação', required=False, initial=senha_homologacao)
    desenvolvedores = forms.MultipleModelChoiceFieldPlus(
        label='Desenvolvedores',
        queryset=User.objects.filter(groups=Group.objects.get(name='Desenvolvedor')),
        help_text='Vincule usuários desenvolvedores desta demanda.',
        required=True,
        initial=desenvolvedores_demanda,
    )
    analistas = forms.MultipleModelChoiceFieldPlus(
        label='Analistas',
        queryset=User.objects.filter(groups=Group.objects.get(name='Analista')),
        help_text='Vincule usuários analistas desta demanda.',
        required=True,
        initial=analistas_demanda,
    )
    ambiente_homologacao = forms.ModelChoiceFieldPlus(
        label='Ambiente de Homologação', queryset=AmbienteHomologacao.objects, required=False, help_text=mark_safe("Caso ainda não tenha um, <a class='popup' href='/admin/demandas/ambientehomologacao/add/'>crie um Ambiente de Homologação</a>.")
    )

    id_merge_request = forms.IntegerFieldPlus(label='ID Merge-request', required=False)

    base_fields = {
        Situacao.ESTADO_EM_NEGOCIACAO: {'comentario': comentario, 'analistas': analistas},
        Situacao.ESTADO_EM_ANALISE: {'comentario': comentario, 'data_previsao': data_previsao},
        Situacao.ESTADO_APROVADO: {'comentario': comentario},
        Situacao.ESTADO_EM_DESENVOLVIMENTO: {'comentario': comentario, 'data_previsao': data_previsao, 'desenvolvedores': desenvolvedores},
        Situacao.ESTADO_EM_HOMOLOGACAO: {
            'comentario': comentario,
            'data_conclusao': data_conclusao,
            'data_previsao': data_previsao,
            'ambiente_homologacao': ambiente_homologacao,
            'url_validacao': url_validacao,
            'senha_homologacao': senha_homologacao,
        },
        Situacao.ESTADO_HOMOLOGADA: {'comentario': comentario},
        Situacao.ESTADO_CANCELADO: {'comentario': comentario},
        Situacao.ESTADO_SUSPENSO: {'comentario': comentario},
        Situacao.ESTADO_CONCLUIDO: {'comentario': comentario, 'data_conclusao': data_conclusao},
        Situacao.ESTADO_EM_IMPLANTACAO: {'comentario': comentario, 'data_previsao': data_previsao, 'id_merge_request': id_merge_request},
        'default': {'comentario': comentario, 'data_conclusao': data_conclusao, 'data_previsao': data_previsao},
    }

    if situacao in base_fields:
        situacao_form_factory = situacao

    def clean(self, *args, **kwargs):
        data_previsao = self.cleaned_data.get('data_previsao')
        data_conclusao = self.cleaned_data.get('data_conclusao')

        if data_previsao and data_conclusao:
            if data_previsao < data_conclusao:
                self.add_error('data_conclusao', 'A Data de Previsão não pode ser menor que a última Data de Conclusão.')

        ambiente_homologacao = self.cleaned_data.get('ambiente_homologacao')
        if ambiente_homologacao:
            self.cleaned_data['url_validacao'] = ''
            self.cleaned_data['senha_homologacao'] = ''

        return self.cleaned_data

    fieldsets = ((None, {'fields': ('comentario', 'desenvolvedores', 'analistas', 'data_conclusao', 'data_previsao', 'ambiente_homologacao', 'url_validacao', 'senha_homologacao', 'id_merge_request')}),)

    return type('SituacaoAlterarForm', (forms.BaseForm,), {'base_fields': base_fields[situacao_form_factory], 'fieldsets': fieldsets, 'METHOD': 'POST', 'clean': clean})


class DataPrevisaoAlterarForm(forms.FormPlus):
    comentario = forms.CharField(
        label='Comentário',
        required=True,
        widget=forms.Textarea(attrs={'rows': '50', 'cols': '100'}),
        help_text='Justifique a edição da Data de Previsão desta etapa. Este comentário será visualizado por todos os interessados da demanda.',
    )
    data_previsao = DateFieldPlus(label='Previsão', required=True, help_text='Informe a Data de Previsão para conclusão desta etapa')

    fieldsets = (('Alterar Data de Previsão da Etapa', {'fields': ('data_previsao', 'comentario')}),)


class NotaInternaForm(forms.ModelForm):
    class Meta:
        model = NotaInterna
        fields = ('nota',)

    def __init__(self, *args, **kwargs):
        demanda = kwargs.pop('demanda')
        super().__init__(*args, **kwargs)

        if not hasattr(self.instance, 'demanda'):
            self.instance.demanda = demanda

        if self.instance.demanda is None:
            self.instance.demanda = demanda


class AnexosForm(forms.ModelForm):
    class Meta:
        model = Anexos
        fields = ('arquivo',)

    def __init__(self, *args, **kwargs):
        usuario = kwargs.pop('usuario')
        demanda = kwargs.pop("demanda")

        super().__init__(*args, **kwargs)

        self.instance.usuario = usuario
        self.instance.demanda = demanda


class DashboardForm(forms.FormPlus):
    inicio = forms.DateFieldPlus(label='Data Inicial', required=False)
    final = forms.DateFieldPlus(label='Data Final', required=False)
    tag = forms.ModelChoiceField(label='Tag', queryset=Tag.objects, required=False)


class AcompanhamentoForm(forms.FormPlus):
    area = forms.ModelChoiceField(
        queryset=AreaAtuacaoDemanda.objects.all(), widget=AutocompleteWidget(search_fields=AreaAtuacaoDemanda.SEARCH_FIELDS),
        label='Área de Atuação', required=False
    )
    inicio = forms.DateFieldPlus(label='Data Inicial', required=True)
    final = forms.DateFieldPlus(label='Data Final', required=True)


class RelatorioForm(forms.FormPlus):
    inicio = forms.DateFieldPlus(label='Data Inicial', required=True)
    final = forms.DateFieldPlus(label='Data Final', required=True)


class AtualizacaoForm(forms.ModelFormPlus):
    tags = forms.MultipleModelChoiceFieldPlus(Tag.objects, label='Tags', required=True)
    grupos = forms.MultipleModelChoiceFieldPlus(Group.objects, label='Grupos Envolvidos', required=False)
    demanda = forms.ModelChoiceField(
        queryset=Demanda.objects.filter(situacao=Situacao.ESTADO_CONCLUIDO),
        widget=AutocompleteWidget(search_fields=Demanda.SEARCH_FIELDS),
        label='Demanda Vinculada',
        required=False,
    )
    responsaveis = forms.MultipleModelChoiceFieldPlus(
        label='Responsáveis',
        queryset=User.objects,
        help_text='Vincule usuários desenvolvedores desta atualização.',
        required=False,
    )

    class Meta:
        model = Atualizacao
        exclude = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data'].initial = datetime.now().date()
        self.fields['responsaveis'].queryset = User.objects.filter(groups=Group.objects.get(name='Desenvolvedor'))


class NovaPrioridadeDemandaForm(forms.FormPlus):
    nova_prioridade = forms.IntegerField(min_value=0, required=True)


class SugestaoMelhoriaAddForm(forms.ModelFormPlus):
    requisitante_info = forms.CharField(
        label='Requisitante',
    )
    area_atuacao_info = forms.CharField(
        label='Área de Atuação',
    )
    tags_info = forms.CharField(
        label='Módulo',
    )
    interessados = forms.MultipleModelChoiceFieldPlus(
        label='Interessados',
        queryset=User.objects.filter(is_active=True),
        required=False
    )

    class Meta:
        model = SugestaoMelhoria
        fields = ('requisitante_info', 'area_atuacao_info', 'tags_info', 'titulo', 'descricao', 'interessados')

    def __init__(self, *args, **kwargs):
        self._area_atuacao = kwargs.pop('area_atuacao')
        self._tags = kwargs.pop('tags')
        self._user_requisitante = kwargs.pop('user_requisitante')

        assert self._area_atuacao and self._tags and self._user_requisitante

        super().__init__(*args, **kwargs)

        field_requisitante_info = self.fields['requisitante_info']
        field_requisitante_info.initial = '{}'.format(self._user_requisitante)
        field_requisitante_info.widget.attrs['readonly'] = 'readonly'

        field_area_atuacao_info = self.fields['area_atuacao_info']
        field_area_atuacao_info.initial = '{}'.format(self._area_atuacao)
        field_area_atuacao_info.widget.attrs['readonly'] = 'readonly'

        field_tags_info = self.fields['tags_info']
        field_tags_info.initial = '{}'.format(', '.join('{}'.format(_) for _ in self._tags))
        field_tags_info.widget.attrs['readonly'] = 'readonly'

    def save(self, commit=True):
        self.instance.area_atuacao = self._area_atuacao
        self.instance.requisitante = self._user_requisitante
        save = super().save(commit)
        if save:
            self.instance.tags.set(self._tags)
        return save


class SugestaoMelhoriaEdicaoBasicaForm(forms.ModelFormPlus):
    interessados = forms.MultipleModelChoiceFieldPlus(
        label='Interessados',
        queryset=User.objects.filter(is_active=True),
        required=False
    )

    class Meta:
        model = SugestaoMelhoria
        fields = ('titulo', 'descricao', 'interessados',)


class SugestaoMelhoriaEdicaoCompletaForm(forms.ModelFormPlus):
    interessados = forms.MultipleModelChoiceFieldPlus(
        label='Interessados',
        queryset=User.objects.filter(is_active=True),
        required=False
    )
    modulo = forms.ModelChoiceFieldPlus(
        label='Módulo',
        queryset=Tag.objects,
    )
    responsavel = forms.ModelChoiceFieldPlus(
        label='Responsável',
        queryset=User.objects.filter(is_active=True),
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['modulo'].initial = self.instance.tags.first().id
        self.fields['modulo'].queryset = self.instance.area_atuacao.tags_relacionadas
        self.fields['modulo'].help_text = 'Módulos de {}'.format(self.instance.area_atuacao.area.nome)

    class Meta:
        model = SugestaoMelhoria
        fields = ('titulo', 'descricao', 'interessados', 'modulo', 'responsavel', 'situacao')


class SugestaoMelhoriaEdicaoAreaAtuacaoForm(forms.ModelFormPlus):

    class Meta:
        model = SugestaoMelhoria
        fields = ('area_atuacao',)


class AmbienteHomologacaoForm(forms.ModelFormPlus):
    banco = forms.ChoiceField(label='Banco', choices=[])

    class Meta:
        model = AmbienteHomologacao
        fields = 'criador', 'branch', 'banco', 'data_expiracao', 'senha'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        bancos = Configuracao.get_valor_por_chave('demandas', 'bancos_suapdevs') or 'suap'
        self.fields['banco'].choices = [(x, x) for x in bancos.split()]
        self.fields['criador'].initial = AnalistaDesenvolvedor.objects.filter(usuario_id=self.request.user.id).first()
        self.fields['senha'].initial = self.sugestao_senha()

    def clean_branch(self):
        branch = self.cleaned_data['branch']
        if branch not in gitlab.list_branche_names(branch):
            raise forms.ValidationError('Branch inválida.')
        return branch

    def sugestao_senha(self):
        hash = hashlib.sha1()
        hash.update(str(time.time()).encode('utf-8'))
        return hash.hexdigest()[:6]


class ExecutarComandoForm(forms.FormPlus):
    comando = forms.CharFieldPlus(label='python manage.py')

    def clean_comando(self):
        raise forms.ValidationError('Funcionalidade ainda não implementada')
