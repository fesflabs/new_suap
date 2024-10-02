import base64
import cgi
import json
import mimetypes
import os
import re
import shutil
import socket
import string
import tempfile
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import date, datetime, timedelta
from decimal import Decimal
from functools import cmp_to_key
from os import path
from os.path import join

import yaml
from django.core.files.storage import default_storage
from django.utils.crypto import get_random_string
from sentry_sdk import capture_exception

from bs4 import BeautifulStoneSoup
from dateutil.relativedelta import relativedelta
from django import forms
from django.apps import apps
from django.conf import settings
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models.aggregates import Sum
from django.db.models.fields.related import ManyToManyField
from django.http import HttpResponse
from django.template.defaultfilters import slugify
from django.utils.safestring import mark_safe
from django_tables2 import RequestConfig, Table
from django_tables2.tables import DeclarativeColumnsMetaclass

from djtools import pdf
from djtools.storages import cache_file
from djtools.utils import get_tl, str_money_to_decimal, to_ascii, deprecated

tl = get_tl()

CODIFICACAO_ARQUIVOS_IMPORTACAO = 'latin-1'

FLAG_LOG_GERENCIAMENTO_GRUPO = 99


def registrar_remocao_grupo(sender, **kwargs):
    registrar_historico_grupo('Removido(a) do grupo', sender, **kwargs)


def registrar_adicao_grupo(sender, **kwargs):
    if kwargs['created']:
        registrar_historico_grupo('Adicionado(a) ao grupo', sender, **kwargs)


def registrar_historico_grupo(acao, sender, **kwargs):
    usuario_grupo = kwargs['instance']
    usuario = usuario_grupo.user
    grupo = usuario_grupo.group
    registrar_log_entry(usuario, grupo, acao)


def registrar_inclusao_remocao_grupo(sender, **kwargs):
    action = kwargs['action']
    if action in ('pre_clear', 'pre_remove', 'post_add'):
        usuario = kwargs['instance']
        pks = kwargs['pk_set'] or []
        acao = 'Adicionado(a) ao grupo' if action == 'post_add' else 'Removido(a) do grupo'
        if action == 'pre_remove' and not sender.objects.filter(user_id=usuario, group_id__in=pks).exists():
            return
        elif action == 'pre_clear':
            pks = sender.objects.filter(user_id=usuario).values_list('group_id', flat=True)

        for grupo in Group.objects.filter(pk__in=pks):
            registrar_log_entry(usuario, grupo, acao)


def registrar_log_entry(usuario, grupo, acao):
    from comum.models import User
    usuario_logado = tl.get_user()
    if usuario_logado and usuario_logado.pk and User.objects.filter(pk=usuario_logado.pk).exists():
        entry = LogEntry()
        entry.user = usuario_logado
        entry.object_id = usuario.id
        entry.content_type = ContentType.objects.get_for_model(type(usuario))
        entry.object_repr = str(usuario)
        entry.action_flag = FLAG_LOG_GERENCIAMENTO_GRUPO
        entry.change_message = f'{acao} {grupo}'
        entry.save()


def get_setor(user=None):
    user = user or tl.get_user()
    try:
        return user.get_relacionamento().setor
    except Exception:
        pass
    try:
        return user.get_relacionamento().curso_campus.diretoria.setor
    except Exception:
        return None


def get_uo(user=None):
    user = user or tl.get_user()

    if 'rh' in settings.INSTALLED_APPS:
        PessoaFisica = apps.get_model("rh", "PessoaFisica")
        if isinstance(user, PessoaFisica):
            user = user.user

    try:
        return user.get_relacionamento().setor.uo
    except Exception:
        pass
    try:
        return user.get_relacionamento().curso_campus.diretoria.setor.uo
    except Exception:
        return None


def get_cargo_emprego(user=None):
    user = user or tl.get_user()
    try:
        return user.get_relacionamento().cargo_emprego
    except Exception:
        return None


def get_sigla_reitoria():
    from comum.models import Configuracao

    return Configuracao.get_valor_por_chave('comum', 'reitoria_sigla') or 'RE'


def get_setor_siape(user=None):
    """Retorna o setor de exercício SIAPE"""
    user = user or tl.get_user()
    try:
        return user.get_relacionamento().setor_exercicio
    except Exception:
        return None


def get_uo_siape(user=None):
    """Retorna a UO do setor de exercício SIAPE"""
    user = user or tl.get_user()
    setor_siape = get_setor_siape(user)
    try:
        return setor_siape.uo
    except Exception:
        return None


def get_todos_setores(user=None, setores_compartilhados=True):
    # TODO: Isso não deveria ser um método da classe Funcionario?
    """
    Setores em 3 situações serão incluídos neste retorno:
     - Setor de lotação (FK setor do funcionario)
     - Setores adicionais da pessoa (``setores_adicionais``)
     - Setores compartilhados do Setor (``setores_compartilhados``)
    """
    user = user or tl.get_user()
    Setor = apps.get_model('rh', 'Setor')
    profile = user.get_profile()
    ids_setores = list()
    if hasattr(profile, 'setores_adicionais'):
        ids_setores = list(profile.setores_adicionais.values_list('id', flat=True))

    setor_origem = None
    try:
        setor_origem = get_setor(user)
    except Exception:
        pass
    if setor_origem:
        ids_setores.append(setor_origem.id)
        if setores_compartilhados:
            ids_setores += list(setor_origem.setores_compartilhados.values_list('id', flat=True))

    if user.get_relacionamento().papeis_ativos:
        ids_setores += list(user.get_relacionamento().papeis_ativos.values_list('setor_suap', flat=True))
    return Setor.objects.filter(id__in=ids_setores)


def get_setor_cppd():
    #   PK do CPPD
    from rh.models import Setor

    return Setor.objects.get(pk=709)


def get_ids_meus_setores_hoje(user=None):
    ids_setores = [get_setor(user).pk]
    Funcao = apps.get_model('rh', 'Funcao')
    if user.eh_servidor:
        ids_setores += (
            user.get_relacionamento()
            .historico_funcao(date.today(), date.today())
            .filter(funcao__codigo__in=Funcao.get_codigos_funcao_chefia())
            .values_list('setor_suap_id', flat=True)
        )
    return ids_setores


def get_meus_setores_hoje(user=None):
    Setor = apps.get_model('rh', 'Setor')
    ids = get_ids_meus_setores_hoje(user)
    if not ids:
        setores = Setor.objects.none()
    else:
        setores = Setor.objects.filter(id__in=ids)
    return setores


def get_setores_que_sou_chefe_hoje(user=None):
    Setor = apps.get_model('rh', 'Setor')
    vinculo = user.get_relacionamento()
    ids_setores = []
    Funcao = apps.get_model('rh', 'Funcao')
    if type(vinculo) == apps.get_model('rh', 'Servidor'):
        ids_setores += vinculo.historico_funcao(date.today(), date.today()).filter(funcao__codigo__in=Funcao.get_codigos_funcao_chefia()).values_list('setor_suap_id', flat=True)
    return Setor.objects.filter(id__in=ids_setores)


def get_todos_campi(user=None):
    # TODO: Isso não deveria ser um método da classe Funcionario?
    UnidadeOrganizacional = apps.get_model('rh', 'UnidadeOrganizacional')
    todos_setores = get_todos_setores(user)
    return UnidadeOrganizacional.objects.suap().filter(id__in=todos_setores.values_list('uo', flat=True))


def get_topo_pdf(titulo=None):
    # Mover para um módulo pdf_utils?
    # Deve ser utilizado com papel A4
    IMAGE_PATH = join(settings.STATIC_ROOT, 'comum/img/brasao_cinza.jpg')
    TITULO = apps.get_model('comum', 'configuracao').get_valor_por_chave('comum', 'instituicao')
    image = pdf.Image(IMAGE_PATH, width=15.96 * pdf.mm, height=17.4 * pdf.mm)

    tabela_imagem = pdf.table([[image, pdf.para(TITULO, align='center', fontsize='12')]], w=[25, 165], grid=0)

    elementos = [tabela_imagem, pdf.space(4)]

    if titulo:
        elementos.append(pdf.para(titulo, style='h2', align='center'))
        elementos.append(pdf.space(4))

    return elementos


def extrai_matricula(matricula):
    # TODO: Função específica para tratar arquivos do SIAPE. Poderia estar num
    #       módulo utilitário específico para isso. siape_utils?
    """
    Recebe '262180277123' e retorna '277123'
    """
    return str(int(matricula[:12][-7:]))


def capitaliza_nome(nome):
    if not nome:
        return nome
    lnome = []
    prep = ("da", "de", "di", "do", "du", "das", "dos", "e")
    for i in nome.lower().split():
        if i not in prep:
            i = i.capitalize()
        lnome.append(i)
    return ' '.join(lnome)


def retirar_preposicoes_nome(nome):
    preposicoes = ("da", "de", "di", "do", "du", "das", "dos", "e")
    nova_palavra = []
    for token in nome.split():
        if token.lower() not in preposicoes:
            nova_palavra.append(token)
    return ' '.join(nova_palavra)


def normalizar_termos_busca(busca, avoid_short_search=True):
    preposicoes = ("da", "de", "di", "do", "du", "das", "dos", "e")
    nova_palavra = []
    retiradas = []
    for token in busca.split():
        if not avoid_short_search or (token.lower() not in preposicoes and len(token) > 2):
            nova_palavra.append(token)
        else:
            retiradas.append(f'"{token}"')
    return ' '.join(nova_palavra), ', '.join(retiradas)


MENU_APP_ORDER = ['documento_eletronico', 'processo_eletronico', 'edu', 'pesquisa', 'projetos', 'rh']


@deprecated('Utilizar colocar_menu_na_cache')
def get_json_from_file(app):
    filepath = path.join(settings.BASE_DIR, app, 'menu.json')
    retorno = []
    if settings.LPS:
        filepath_lps = path.join(settings.BASE_DIR, app, 'lps', settings.LPS, 'menu.json')
        if path.isfile(filepath_lps):
            filepath = filepath_lps

    if path.isfile(filepath):
        with open(filepath, encoding='utf-8') as data_file:
            try:
                retorno += json.load(data_file)
            except Exception:
                print(filepath)
    return retorno


def get_menu_from_file(app):
    filepath = path.join(settings.BASE_DIR, app, 'menu.yaml')
    retorno = []
    if settings.LPS:
        filepath_lps = path.join(settings.BASE_DIR, app, 'lps', settings.LPS, 'menu.yaml')
        if path.isfile(filepath_lps):
            filepath = filepath_lps

    if path.isfile(filepath):
        with open(filepath, encoding='utf-8') as data_file:
            try:
                dic = yaml.safe_load(data_file)
                lista = []
                for key, value in dic.items():
                    obj = {}
                    obj['hierarchy'] = key
                    for k, v in value.items():
                        obj[k] = v
                    lista.append(obj)
                retorno += lista
            except Exception:
                print(filepath)
    return retorno


def colocar_menu_na_cache():
    if not cache.get('menus'):
        menu_json = []
        for app in MENU_APP_ORDER:
            if app in settings.INSTALLED_APPS_SUAP:
                menu_json += get_menu_from_file(app)
        for app in settings.INSTALLED_APPS_SUAP + ('djtools',):
            if not app in MENU_APP_ORDER:
                menu_json += get_menu_from_file(app)

        cache.set('menus', menu_json, 60)
    return cache.get('menus') or []


cache.delete('menus')

ORDER_DEFAULT = 99
MENU_ITEMS_ORDER = dict()


def compare_order_nodes(a, b):
    order_a = MENU_ITEMS_ORDER.get(f"{a['hierarchy']}::{a['label']}") or ORDER_DEFAULT
    order_b = MENU_ITEMS_ORDER.get(f"{b['hierarchy']}::{b['label']}") or ORDER_DEFAULT
    if order_a > order_b:
        return 1
    elif order_a == order_b:
        return 0
    else:
        return -1


def get_menu_json_as_html(user):
    menu_items = []  # Lista dos itens de menu; cada item é o raiz com seus filhos
    menu_items_index = dict()  # Controle dos raízes

    def add_item(path, url):
        for idx, i in enumerate(path):
            path_idx = '::'.join(path[: idx + 1])
            eh_folha = idx == len(path) - 1
            # Primeiro Elemento Raiz
            if idx == 0 and path_idx not in menu_items_index:
                item = dict(hierarchy=None, label=i, children=[], css_class=to_ascii(slugify(i.lower())))
                menu_items.append(item)
                menu_items_index[path_idx] = item
            # Nao eh primeiro nem ultimo
            elif not eh_folha:
                if path_idx not in menu_items_index:
                    item = dict(hierarchy='::'.join(path_idx.split("::")[0:-1]), label=i, children=[])
                    menu_items_index[path_idx] = item
                    menu_items_index['::'.join(path[:idx])]['children'].append(item)
            else:  # Folha
                id_ = '_'.join([re.sub(r'\W', '', i.lower()) for i in path])
                item = dict(hierarchy='::'.join(path_idx.split("::")[0:-1]), label=i, url=url, id_=id_)
                menu_items_index['::'.join(path[:idx])]['children'].append(item)

    def get_items_as_li(node):
        nodes = []
        __get_descendents_helper(node, nodes)
        return ''.join(nodes)

    def __get_descendents_helper(node, nodes):
        node_children = node.get('children', [])
        node_children = sorted(node_children, key=cmp_to_key(lambda a, b: compare_order_nodes(a, b)))
        css = node.get('css_class', b'')
        css_class = []
        if node_children:
            css_class.append('has-child')
        if node.get('css_class'):
            css_class.append('menu-' + css)
        css_class = ' '.join(css_class)

        url = "#"
        icon = ''
        if css:
            icon = f'<span class="fas fa-{css}" aria-hidden="true"></span>'
        id_ = ""
        if node.get('url'):
            url = '/djtools/breadcrumbs_reset/'
            icon = ''
            if node.get('id_'):
                id_ = 'id="menu-item-{}"'.format(node.get('id_'))
                url += '{}'.format(node.get('id_'))
            if node.get('url'):
                url += node.get('url')
            if not url.endswith('/') and '?' not in url:
                url += '/'

        nodes.append('<li class="{}" {}><a href="{}" title="{}">{} <span>{}</span></a>'.format(css_class, id_, url, node['label'], icon, node['label']))

        if node_children:
            nodes.append('<ul>')
        for c in node_children:
            __get_descendents_helper(c, nodes)
        if node_children:
            nodes.append('</ul>')
        nodes.append('</li>')
        return nodes

    user_groups = user.groups.values_list('name', flat=True)
    if user.is_superuser:
        user_groups = Group.objects.all().values_list('name', flat=True)
    user_permissions = user.get_all_permissions()
    # Guardar conteúdos dos menu.xml em memória
    menu = colocar_menu_na_cache()
    for item_menu in menu:
        # Verificando se o usuário tem direito ao item
        show_item = False
        from comum.models import Configuracao
        has_required_config = False
        if item_menu.get('config_required') and any([bool(Configuracao.get_valor_por_chave(*each.split('.'))) for each in item_menu['config_required']]):
            has_required_config = True
        elif not item_menu.get('config_required'):
            has_required_config = True
        if has_required_config:
            if not item_menu.get('permissions_required') and not item_menu.get('groups_required'):
                show_item = True
            elif item_menu.get('permissions_required') and any([each in item_menu['permissions_required'] for each in user_permissions]):
                show_item = True
            elif item_menu.get('groups_required') and any([each in item_menu['groups_required'] for each in user_groups]):
                show_item = True
        if not show_item:
            continue
        hierarchy = item_menu.get('hierarchy')
        if item_menu.get('order'):
            MENU_ITEMS_ORDER['::'.join(hierarchy.split("::"))] = item_menu.get('order')
        if item_menu.get('url'):
            add_item(hierarchy.split('::'), url=item_menu.get('url'))

    menu_html = []
    for i in menu_items:
        menu_html.append(get_items_as_li(i))
    return ''.join(menu_html)


def agrupar_em_pares(lista):
    """
    [0, 1, 2, 3, 4, 5, 6] --> [[0, 1], [2, 3], [4, 5], [6]]
    """
    lista_pares = []
    for index, item in enumerate(lista):
        if index % 2 == 0:
            lista_pares.append([item])
        else:
            lista_pares[-1].append(item)
    return lista_pares


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days + 1)):
        yield start_date + timedelta(n)


def existe_conflito_entre_intervalos(datas):
    datas = agrupar_em_pares(datas)

    for data in datas:
        dataInicioIntervalo = data[0]
        dataFimIntervalo = data[1]

        for data2 in datas:
            if data != data2:
                dataInicioIntervalo2 = data2[0]
                dataFimIntervalo2 = data2[1]

                if dataInicioIntervalo >= dataInicioIntervalo2 and dataInicioIntervalo <= dataFimIntervalo2:
                    return True

                if dataFimIntervalo >= dataInicioIntervalo2 and dataFimIntervalo <= dataFimIntervalo2:
                    return True
    return False


def adicionar_mes(data, meses=1):
    return data + relativedelta(months=meses)


class TableReportPlus(Table):
    tfoot_sum = dict()

    class Meta:
        template_name = "comum/templates/table_plus.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.param_report = 'relatorio'

    def add_sum_table_foot(self, collumn, conditions=None):
        self.tfoot_sum[collumn] = conditions

    def get_sum_foot(self, column):
        if column in self.tfoot_sum:
            if self.tfoot_sum[column] is not None:
                return (self.data.data.filter(**self.tfoot_sum[column]['+']).aggregate(Sum(column))["{}__sum".format(column)] or Decimal(0.0)) - (
                    self.data.data.filter(**self.tfoot_sum[column]['-']).aggregate(Sum(column))["{}__sum".format(column)] or Decimal(0.0)
                )

            return self.data.data.aggregate(Sum(column))["{}__sum".format(column)]

    def get_foot_collumns(self):
        foot_collumns = []
        for column in self._sequence:
            if column in self.tfoot_sum:
                foot_collumns.append(self.get_sum_foot(column))
            else:
                foot_collumns.append("")
        return foot_collumns

    def get_params(self):
        dicionario = dict()
        for coluna in self.columns.names():
            dicionario[coluna.upper().replace('_', ' ').split('.')[-1]] = self.columns.columns[coluna].accessor
        return self.data.data, dicionario


def get_table(**kwargs):
    if 'request' in kwargs:
        request = kwargs.pop('request')
    else:
        request = get_tl().get_request()

    if 'queryset' not in kwargs:
        raise ValueError("Não há queryset definida.")

    queryset = kwargs.pop('queryset')
    table_fields = ()
    if 'fields' in kwargs:
        table_fields = kwargs.pop('fields')

    exclude_fields = ()
    if 'exclude_fields' in kwargs:
        exclude_fields = kwargs.pop('exclude_fields')

    custom_fields = dict()
    if 'custom_fields' in kwargs:
        custom_fields = kwargs.pop('custom_fields')

    if not 'per_page_field' in kwargs:
        kwargs['per_page_field'] = 20

    to_export = True
    if 'to_export' in kwargs:
        to_export = kwargs.pop('to_export')

    class OnTheFlyTable(TableReportPlus):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

        class Meta:
            model = queryset.model
            fields = table_fields
            exclude = exclude_fields

    CustomOnTheFlyTable = DeclarativeColumnsMetaclass('CustomOnTheFlyTable', (OnTheFlyTable,), custom_fields)

    def eh_many2many(modelo, caminho):
        _caminho = caminho.split('.')
        try:
            campo = modelo._meta.get_field(_caminho[0])
        except FieldDoesNotExist:
            return False

        if isinstance(campo, ManyToManyField):
            return True

        if len(_caminho) == 1:
            return False

        if isinstance(campo, models.ForeignKey):
            return eh_many2many(campo.remote_field.model, '.'.join(_caminho[1:]))
        else:
            return eh_many2many(campo.model, '.'.join(_caminho[1:]))

    def my_render(self, value):
        if value.all().exists():
            unicode_list = []
            for objeto in value.all():
                unicode_list.append(str(objeto))
            return mark_safe(", ".join(unicode_list))
        return "-"

    for table_field in table_fields:
        if eh_many2many(queryset.model, table_field):
            name = 'render_' + table_field
            method = my_render
            method.__name__ = name
            setattr(CustomOnTheFlyTable, name, method)

    tabela = CustomOnTheFlyTable(queryset, **kwargs)
    RequestConfig(request, paginate=kwargs['per_page_field']).configure(tabela)
    tabela.to_export = to_export
    return tabela


# Verifica se o arquivo obedece ao layout Estava em migracao.py
def compara_modelo(arq, modelo_layout):
    ini = 0
    for metadado in modelo_layout['campos']:
        tipo = modelo_layout['campos'][metadado]['tipo']
        tamanho = modelo_layout['campos'][metadado]['tamanho']
        fim = ini + tamanho
        if tipo == 'N':
            if arq[ini:fim].strip().isdigit() or arq[ini:fim].strip() == '':
                pass
            else:
                raise forms.ValidationError('Layout inválido! Campo {}-"{}" igual a "{}"?'.format(metadado, modelo_layout['campos'][metadado]['nome'], arq[ini:fim]))

        ini = fim


def compara_arquivo_ao_modelo(cleaned_data, modelo):
    if cleaned_data:
        cleaned_data.seek(0)
        primeira_linha = None
        for linha in cleaned_data.readlines():
            primeira_linha = str(linha, CODIFICACAO_ARQUIVOS_IMPORTACAO)
            break
        cleaned_data.seek(0)
        compara_modelo(primeira_linha, modelo)
    return cleaned_data


def ha_choque_de_periodo(lista_periodos, periodo_teste, retornar_periodo_choque=False):
    '''
     lista_periodos = ((data1, data2),(data1, data2),...)
     periodo_teste = (data1, data2)

             A---------B
      C-----D     OU    C-----D

      (D < A) OU (C > B) --> O período C---D não conflita.

      retorna True/False + o período de "choque"

    '''
    ha_choque = False
    periodo_choque_data_inicio = None
    periodo_choque_data_fim = None
    for d1, d2 in lista_periodos:
        if not (periodo_teste[1] < d1 or periodo_teste[0] > d2):
            ha_choque = True
            periodo_choque_data_inicio = d1
            periodo_choque_data_fim = d2
            break  # sai na primeira ocorrência

    if retornar_periodo_choque:
        return ha_choque, periodo_choque_data_inicio, periodo_choque_data_fim
    else:
        return ha_choque


def get_logo_instituicao_file_path(force=False):
    from comum.models import Configuracao
    logo_nome_arquivo = Configuracao.get_valor_por_chave('comum', 'logo_instituicao')
    if not logo_nome_arquivo:
        return os.path.join(settings.BASE_DIR, 'comum/static/comum/img/logo.jpg')
    try:
        return cache_file(logo_nome_arquivo, force=force)
    except Exception:
        return ''


def get_logo_instituicao_fundo_transparente_file_path(force=False):
    from comum.models import Configuracao
    logo_nome_arquivo = Configuracao.get_valor_por_chave('comum', 'logo_instituicao_fundo_transparente')
    if not logo_nome_arquivo:
        return os.path.join(settings.BASE_DIR, 'comum/static/comum/img/logo_capa.png')
    try:
        return cache_file(logo_nome_arquivo, force=force)
    except Exception:
        return ''


def get_logo_instituicao_url():
    from comum.models import Configuracao

    logo_nome_arquivo = Configuracao.get_valor_por_chave('comum', 'logo_instituicao')
    if logo_nome_arquivo:
        return default_storage.url(logo_nome_arquivo)
    return '/static/comum/img/logo.jpg'


def get_logo_instituicao_fundo_transparente_url():
    from comum.models import Configuracao

    logo_nome_arquivo = Configuracao.get_valor_por_chave('comum', 'logo_instituicao_fundo_transparente')
    if logo_nome_arquivo:
        return default_storage.url(logo_nome_arquivo)
    return '/static/comum/img/logo_capa.png'


def suap_context_processor(request):
    """
    Essa função é chamada no fim do processamento de cada view
    """
    from comum.models import Configuracao, Preferencia, RegistroNotificacao

    if request.user is None:
        return dict()

    if not request.session.get('menu_as_html', ''):  # O usuário acabou de logar
        request.session['get_setor'] = get_setor(request.user)
        request.session['get_uo'] = get_uo(request.user)
        request.session['menu_as_html'] = get_menu_json_as_html(request.user)

    display_email = None
    if settings.DEBUG:
        emails_file_path = 'deploy/emails.json'
        display_email = os.path.exists(emails_file_path)

    notificacoes_nao_lidas = 0
    try:
        nome_instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao')
        logo_instituicao_media_url = get_logo_instituicao_url()

        if request.user.is_authenticated:
            notificacoes_nao_lidas = RegistroNotificacao.contar_nao_lidas(request.user)
    except Exception:
        nome_instituicao = ''
        logo_instituicao_media_url = ''

    if (not request.session.get('theme')) and request.user.is_authenticated:
        try:
            preferencia = Preferencia.objects.filter(usuario=request.user).first()
            if preferencia:
                request.session['theme'] = preferencia.tema or Preferencia.PADRAO
            else:
                request.session['theme'] = Preferencia.PADRAO
        except Exception:
            request.session['theme'] = Preferencia.PADRAO

    if not request.session.get('usuario_logado_eh_aluno') and request.user.is_authenticated:
        try:
            request.session['usuario_logado_eh_aluno'] = request.user.get_vinculo() and request.user.get_vinculo().eh_aluno()
        except Exception:
            request.session['usuario_logado_eh_aluno'] = True

    server_alias = getattr(settings, 'SERVER_ALIAS', '')
    host_name = server_alias and f'{server_alias} - {socket.gethostname()}' or socket.gethostname()

    ctx = dict(
        super_template=request.user.is_authenticated and 'admin/base.html' or 'admin/base_anonima.html',
        debug=settings.DEBUG,
        now=datetime.now(),
        usuario_logado_eh_aluno=request.session.get('usuario_logado_eh_aluno', True),
        get_setor=request.session['get_setor'],
        get_uo=request.session['get_uo'],
        menu_as_html=request.session.get('menu_as_html', ''),
        menu_item_id=request.session.get('menu_item_id', ''),
        logo_instituicao_media_url=logo_instituicao_media_url,
        nome_instituicao=nome_instituicao,
        host_name=host_name,
        eh_para_documentar=settings.BEHAVE_AUTO_DOC,
        display_email=display_email,
        is_popup=request.GET.get('_popup'),
        theme=request.session.get('theme', Preferencia.PADRAO),
        notificacoes_nao_lidas=notificacoes_nao_lidas,
        exibir_botao_reportar_erro=not request.path.startswith('/erros') and not request.path.startswith('/admin/erros') and request.user.is_authenticated
    )

    return ctx


def possui_horario_extra_noturno(par):
    saida = par[1]
    if saida.hour >= 22:
        return True


def formata_nome_arquivo(s):
    valid_chars = "-_.() {}{}".format(string.ascii_letters, string.digits)
    filename = ''.join(c for c in s if c in valid_chars)
    filename = filename.replace(' ', '_')
    if filename.startswith('.'):
        return filename[1:]
    return filename


def limitar_tamanho_nome_arquivo(filename, length_limit):
    if len(filename) > length_limit:
        extension = '.{}'.format(filename.split('.')[-1])
        filename = filename[: length_limit - len(extension)]
        filename = '{}{}'.format(filename, extension)
    return filename


def somar_data(data, qtd_dias):
    # TODO: Mover para djtools.utils
    return data + timedelta(qtd_dias)


def proximo_mes(data):
    mes = data.month
    dia = data.day
    while data.month <= mes + 1:
        data = somar_data(data, 1)
        if data.day == dia:
            data = somar_data(data, 1)
            break
    data = somar_data(data, -1)
    return data


def data_extenso(data=None):
    mes_ext = {1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril', 5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto', 9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'}
    data = data or date.today()
    return str(data.strftime('%d de {} de %Y')).format(mes_ext[data.month])


# Funcionalidade de dinheiro por extenso, agradecimentos a https://wiki.python.org.br/MoedaParaTextoPortugues
ext = [
    {
        1: "um",
        2: "dois",
        3: "três",
        4: "quatro",
        5: "cinco",
        6: "seis",
        7: "sete",
        8: "oito",
        9: "nove",
        10: "dez",
        11: "onze",
        12: "doze",
        13: "treze",
        14: "quatorze",
        15: "quinze",
        16: "dezesseis",
        17: "dezessete",
        18: "dezoito",
        19: "dezenove",
    },
    {2: "vinte", 3: "trinta", 4: "quarenta", 5: "cinquenta", 6: "sessenta", 7: "setenta", 8: "oitenta", 9: "noventa"},
    {1: "cento", 2: "duzentos", 3: "trezentos", 4: "quatrocentos", 5: "quinhentos", 6: "seissentos", 7: "setessentos", 8: "oitocentos", 9: "novecentos"},
]

und = ['', ' mil', (' milhão', ' milhões'), (' bilhão', ' bilhões'), (' trilhão', ' trilhões')]


def cent(s, grand):
    s = '0' * (3 - len(s)) + s
    if s == '000':
        return ''
    if s == '100':
        return 'cem'
    ret = ''
    dez = s[1] + s[2]
    if s[0] != '0':
        ret += ext[2][int(s[0])]
        if dez != '00':
            ret += ' e '
        else:
            return ret + (isinstance(und[grand], tuple) and (int(s) > 1 and und[grand][1] or und[grand][0]) or und[grand])
    if int(dez) < 20:
        ret += ext[0][int(dez)]
    else:
        if s[1] != '0':
            ret += ext[1][int(s[1])]
            if s[2] != '0':
                ret += ' e ' + ext[0][int(s[2])]

    return ret + (isinstance(und[grand], tuple) and (int(s) > 1 and und[grand][1] or und[grand][0]) or und[grand])


def extenso(reais, centavos):
    ret = []
    grand = 0
    if int(centavos) == 0:
        ret.append('zero centavos')
    elif int(centavos) == 1:
        ret.append('um centavo')
    else:
        ret.append(cent(centavos, 0) + ' centavos')
    if int(reais) == 0:
        ret.append('zero reais')
        ret.reverse()
        return ' e '.join([r for r in ret if r])
    elif int(reais) == 1:
        ret.append('um real')
        ret.reverse()
        return ' e '.join([r for r in ret if r])
    while reais:
        s = reais[-3:]
        reais = reais[:-3]
        if grand == 0:
            ret.append(cent(s, grand) + ' reais')
        else:
            ret.append(cent(s, grand))
        grand += 1
    ret.reverse()
    return ' e '.join([r for r in ret if r])


def data_normal(data=None):
    """
    Ex: date(2008, 1, 1) --> '01/01/2008'.
    """
    data = data or date.today()
    return data.strftime('%d/%m/%Y')


def extrair_periodo(data_ini, data_fim):
    """
    Retorna string que representa o período entre as datas passadas.
    Ex: date(2008, 1, 1), date(2008, 2, 1) --> '01/01/2008 até '01/02/2008'.
    """
    return '{} até {}'.format(data_ini.strftime('%d/%m/%Y'), data_fim.strftime('%d/%m/%Y'))


def datas_entre(data_ini, data_fim, sabado=True, domingo=True):
    """
    """
    dias = []
    data_atual = data_ini
    while data_atual <= data_fim:
        if not sabado and data_atual.weekday() == 5:
            data_atual = data_atual + timedelta(1)
            continue
        if not domingo and data_atual.weekday() == 6:
            data_atual = data_atual + timedelta(1)
            continue
        dias.append(data_atual)
        data_atual = data_atual + timedelta(1)
    return dias


def meses_entre(data_ini, data_fim):
    """
        Exs:
            08/12/2017 a 17/08/2018 >>>> [12, 1, 2, 3, 4, 5, 6, 7, 8]

                                             2016                    2017                          2018
                                          ----------  -------------------------------------  ----------------------
            08/10/2016 a 17/08/2018 >>>> [10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8]
    """
    meses = []
    for ano in range(data_ini.year, data_fim.year + 1):
        if ano == data_ini.year:
            meses += list(range(data_ini.month, (12 if not data_ini.year == data_fim.year else data_fim.month) + 1))
        elif ano == data_fim.year:
            meses += list(range(1, data_fim.month + 1))
        else:
            meses += list(range(1, 13))
    return meses


def formata_segundos(
    segundos, str_formato_hora='', str_formato_min='', str_formato_seg='', str_formato_omite_se_zero=False  # no padrão '%(h)'  # no padrão '%(m)'  # no padrão '%(s)'
):
    try:
        segundos = int(abs(segundos))
    except Exception:
        segundos = -1
    t_hora = segundos // 3600
    aux = segundos % 3600
    t_minuto = aux // 60
    t_segundo = aux % 60
    dic_tempo = {'h': t_hora, 'm': t_minuto, 's': t_segundo}
    #
    if str_formato_hora or str_formato_min or str_formato_seg:
        if str_formato_omite_se_zero:
            str_formato_hora = '' if dic_tempo['h'] == 0 else str_formato_hora
            str_formato_min = '' if dic_tempo['m'] == 0 else str_formato_min
            str_formato_seg = '' if dic_tempo['s'] == 0 else str_formato_seg
        #
        # retorna a string formatada com os valores de hora, min e seg
        h_m_s = '{}{}{}'.format(str_formato_hora, str_formato_min, str_formato_seg).format(**dic_tempo)
        if not h_m_s:
            return '0h'
        return h_m_s.strip()
    #
    # retorna o dicionário com os valores de hora, min e seg
    return dic_tempo


def formata_segundos_h_min_seg(segundos):
    return formata_segundos(segundos, '{h}h ', '{m}min ', '{s}seg', True)


def somar_qtd(lista_de_listas, indice):
    """Soma índice numa lista de listas"""
    soma = Decimal('0.0')
    for item in lista_de_listas:
        value = item[indice]
        if value is not None:
            if isinstance(value, str):
                soma += str_money_to_decimal(value)
            elif isinstance(value, float) or isinstance(value, int):
                soma += Decimal(str(value))
            elif isinstance(value, Decimal):
                soma += value
    return soma.__int__()


def somar_indice(lista_de_listas, indice):
    """Soma índice numa lista de listas"""
    soma = Decimal('0.0')
    for item in lista_de_listas:
        value = item[indice]
        if value is not None:
            if isinstance(value, str):
                soma += str_money_to_decimal(value)
            elif isinstance(value, float) or isinstance(value, int):
                soma += Decimal(str(value))
            elif isinstance(value, Decimal):
                soma += value
    return soma


def entre_datas(data_ini, data_fim, coluna='data'):
    data_fim = data_fim + timedelta(1)
    return "{coluna} >= '{data_ini}' and {coluna} < '{data_fim}'".format(coluna=coluna, data_ini=data_ini, data_fim=data_fim)


def enviar_para_impressao(ip, porta, texto):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, porta))
    texto = """{}
                        .
                        .
                        .
                        .
                        .
                        .""".format(
        texto
    )
    s.send(texto.encode('latin1'))
    s.close()


# Agrupamento de grupos
# FIXME: Deprecated; o tratamento deve ser por permissão, não por grupo
OPERADOR_ALMOXARIFADO = ['Operador de Almoxarifado', 'Coordenador de Almoxarifado', 'Coordenador de Almoxarifado Sistêmico']
OPERADOR_PATRIMONIO = ['Operador de Patrimônio', 'Coordenador de Patrimônio', 'Coordenador de Patrimônio Sistêmico']
TODOS_GRUPOS_ALMOXARIFADO = ['Operador de Almoxarifado', 'Coordenador de Almoxarifado', 'Coordenador de Almoxarifado Sistêmico', 'Auditor']
OPERADOR_ALMOXARIFADO_OU_PATRIMONIO = OPERADOR_ALMOXARIFADO + OPERADOR_PATRIMONIO


def periodos_sucessivos(periodos):
    """
        periodos = ((date inicial, date final), (date inicial, date final), ... )

        retorna
            FALSE e uma lista de mensagens referentes a:
                - dias conflitantes (sobreposição de períodos)
                - dias descobertos (períodos não sucessivos)
                - períodos com datas inválidas (datas nulas ou data inicial > data final)

            TRUE e sem mensagens.
    """
    lista_mensagens = []

    # dias do periodo completo, considerando todos os periodos
    datas = {}  # datas = {'20141016': 16/10/2014, ...}
    for periodo in periodos:
        # periodo = (data inicial, data final)
        data_inicio = periodo[0]
        data_fim = periodo[1]

        if data_inicio:
            dia_key = data_inicio.strftime('%Y%m%d')
            datas[dia_key] = data_inicio

        if data_fim and (data_fim != data_inicio):
            dia_key = data_fim.strftime('%Y%m%d')
            datas[dia_key] = data_fim

    # menor data e maior data entre os dias do período completo
    menor_data = min(datas.values())
    maior_data = max(datas.values())
    if menor_data and maior_data:
        dias_do_periodo_completo = [menor_data + timedelta(days=dia) for dia in range(0, (maior_data - menor_data).days + 1)]

        dias_do_periodo_completo_ocorrencias = {}
        for dia_do_periodo_completo in dias_do_periodo_completo:
            dia_key = dia_do_periodo_completo.strftime('%Y%m%d')
            if dia_key not in dias_do_periodo_completo_ocorrencias:
                dias_do_periodo_completo_ocorrencias[dia_key] = 0  # inicializa a qtde de ocorrencias da data

        # contabiliza os dias e testa períodos inválidos
        for periodo in periodos:
            # periodo = (data inicial, data final)
            data_inicio = periodo[0]
            data_fim = periodo[1]

            if data_inicio:
                dia_key = data_inicio.strftime('%Y%m%d')
                dias_do_periodo_completo_ocorrencias[dia_key] += 1  # dia coberto

            if data_fim and (data_fim != data_inicio):
                dia_key = data_fim.strftime('%Y%m%d')
                dias_do_periodo_completo_ocorrencias[dia_key] += 1  # dia coberto

            if data_inicio and data_fim:  # período com as 2 datas definidas
                if data_inicio > data_fim:
                    lista_mensagens.append('O período {} a {} tem data final menor que a data inicial. '.format(data_inicio.strftime("%d/%m/%Y"), data_fim.strftime("%d/%m/%Y")))
                else:
                    dias_do_periodo = [data_inicio + timedelta(days=dia) for dia in range(0, (data_fim - data_inicio).days + 1)]
                    for dia_do_periodo in dias_do_periodo:
                        # datas limites do período já "testadas" acima
                        if dia_do_periodo != data_inicio and dia_do_periodo != data_fim:
                            dia_key = dia_do_periodo.strftime('%Y%m%d')
                            dias_do_periodo_completo_ocorrencias[dia_key] += 1  # dia coberto
            else:
                if data_inicio:
                    lista_mensagens.append('O período que se inicia em {} não tem data final. '.format(data_inicio.strftime("%d/%m/%Y")))
                else:
                    lista_mensagens.append('Há períodos sem datas definidas. ')

        # dias/períodos descobertos e dias/período conflitantes
        periodo_descoberto_data_inicial = None
        periodo_descoberto_qtd_dias = 0
        periodo_descoberto_data_fim = None
        periodo_conflitante_data_inicial = None
        periodo_conflitante_qtd_dias = 0
        periodo_conflitante_data_fim = None
        for dia_do_periodo_completo in dias_do_periodo_completo:
            dia_key = dia_do_periodo_completo.strftime('%Y%m%d')

            # dias/períodos descobertos
            if dias_do_periodo_completo_ocorrencias[dia_key] == 0:
                if not periodo_descoberto_data_inicial:
                    periodo_descoberto_data_inicial = dia_do_periodo_completo
                    periodo_descoberto_qtd_dias = 0
                    periodo_descoberto_data_fim = None
                else:
                    periodo_descoberto_qtd_dias += 1
                    dentro_do_mesmo_periodo = (dia_do_periodo_completo - periodo_descoberto_data_inicial).days == periodo_descoberto_qtd_dias

                    if dentro_do_mesmo_periodo:
                        periodo_descoberto_data_fim = dia_do_periodo_completo
                    else:
                        if periodo_descoberto_data_fim:
                            lista_mensagens.append(
                                'O período {} a {} está descoberto. '.format(periodo_descoberto_data_inicial.strftime("%d/%m/%Y"), periodo_descoberto_data_fim.strftime("%d/%m/%Y"))
                            )
                        else:
                            lista_mensagens.append('O dia {} está descoberto. '.format(periodo_descoberto_data_inicial.strftime("%d/%m/%Y")))

                        # inicia novo período
                        periodo_descoberto_data_inicial = dia_do_periodo_completo
                        periodo_descoberto_qtd_dias = 0
                        periodo_descoberto_data_fim = None

            # dias/período conflitantes
            if dias_do_periodo_completo_ocorrencias[dia_key] > 1:
                if not periodo_conflitante_data_inicial:
                    periodo_conflitante_data_inicial = dia_do_periodo_completo
                    periodo_conflitante_qtd_dias = 0
                    periodo_conflitante_data_fim = None
                else:
                    periodo_conflitante_qtd_dias += 1
                    dentro_do_mesmo_periodo = (dia_do_periodo_completo - periodo_conflitante_data_inicial).days == periodo_conflitante_qtd_dias

                    if dentro_do_mesmo_periodo:
                        periodo_conflitante_data_fim = dia_do_periodo_completo
                    else:
                        if periodo_conflitante_data_fim:
                            lista_mensagens.append(
                                'O intervalo de {} a {} está sendo usado em mais de um período. '.format(
                                    periodo_conflitante_data_inicial.strftime("%d/%m/%Y"), periodo_conflitante_data_fim.strftime("%d/%m/%Y")
                                )
                            )
                        else:
                            lista_mensagens.append('O dia {} está sendo usado em mais de um período. '.format(periodo_conflitante_data_inicial.strftime("%d/%m/%Y")))

                        # inicia novo período
                        periodo_conflitante_data_inicial = dia_do_periodo_completo
                        periodo_conflitante_qtd_dias = 0
                        periodo_conflitante_data_fim = None

        # é possível que tenha se iniciado a contagem de um período descoberto sem tê-lo concluído
        if periodo_descoberto_data_inicial:
            if periodo_descoberto_data_fim:
                lista_mensagens.append(
                    'O período {} a {} está descoberto. '.format(periodo_descoberto_data_inicial.strftime("%d/%m/%Y"), periodo_descoberto_data_fim.strftime("%d/%m/%Y"))
                )
            else:
                lista_mensagens.append('O dia {} está descoberto. '.format(periodo_descoberto_data_inicial.strftime("%d/%m/%Y")))

        # é possível que tenha se iniciado a contagem de um período conflitante sem tê-lo concluído
        if periodo_conflitante_data_inicial:
            if periodo_conflitante_data_fim:
                lista_mensagens.append(
                    'O intervalo de {} a {} está sendo usado em mais de um período.'.format(
                        periodo_conflitante_data_inicial.strftime("%d/%m/%Y"), periodo_conflitante_data_fim.strftime("%d/%m/%Y")
                    )
                )
            else:
                lista_mensagens.append('O dia {} está sendo usado em mais de um período. '.format(periodo_conflitante_data_inicial.strftime("%d/%m/%Y")))
    else:
        lista_mensagens.append('Períodos sem datas definidas. ')

    if lista_mensagens:
        return False, lista_mensagens
    else:
        return True, []


def get_setor_propi():
    from comum.models import Configuracao
    from rh.models import Setor

    if Configuracao.get_valor_por_chave('pesquisa', 'setor_propi'):
        return Setor.objects.get(pk=Configuracao.get_valor_por_chave('pesquisa', 'setor_propi'))
    return Setor.objects.get(pk=729)


def get_setor_rh():
    from rh.models import Setor
    from comum.models import Configuracao

    return Setor.objects.filter(pk=Configuracao.get_valor_por_chave('rh', 'setor_rh')).first()


def get_setor_procuradoria():
    from rh.models import Setor
    from comum.models import Configuracao

    return Setor.objects.filter(pk=Configuracao.get_valor_por_chave('rh', 'setor_procuradoria')).first()


def get_setor_auditoria_geral():
    from rh.models import Setor
    from comum.models import Configuracao

    return Setor.objects.filter(pk=Configuracao.get_valor_por_chave('rh', 'setor_auditoria_geral')).first()


def get_setor_proex():
    from comum.models import Configuracao
    from rh.models import Setor

    if Configuracao.get_valor_por_chave('projetos', 'setor_proex'):
        return Setor.objects.get(pk=Configuracao.get_valor_por_chave('projetos', 'setor_proex'))
    return Setor.objects.get(pk=726)


def diferenca_listas(lista1, lista2):
    return list(set(lista1).difference(set(lista2)))


def libreoffice_new_line(tokens, align_center='', font_size=17):
    if len(tokens) > 1:
        if align_center:
            align_center = '<w:jc w:val="center"/>'
        out = ['</w:t></w:r></w:p>']
        for token in tokens:
            out.append('<w:p><w:pPr><w:spacing w:after="0"/>{}</w:pPr><w:r><w:rPr><w:sz w:val="{}"/></w:rPr><w:t>{}'.format(align_center, font_size, token))
            out.append('</w:t></w:r></w:p>')
        del out[-1]
        return ''.join(out)
    elif len(tokens) == 1:
        return tokens[0]
    return ''


def insert_space(string, index):
    if len(string) <= index:
        return string
    return string[:index] + ' ' + string[index:]


def gerar_documento_impressao(dicionario, modelo_documento_path, pdfa=False, imagem_path=None):
    """
    :param dicionario: dados que serão substitutos pelas marcações do docx
    :param modelo_documento_path: caminho do arquivo docx contendo as marcações que serão substituidas
    :param pdfa: informar None caso deseje que o próprio docx seja retorna.
        informar True caso deseje que o docx seja convertido para PDF-A
        informar False caso deseje que o docx seja conertido para PDF
    :return: caminho do arquivo resultante do processamento
    """
    template_docx = zipfile.ZipFile(modelo_documento_path)
    new_docx = zipfile.ZipFile(os.path.join(settings.TEMP_DIR, f'temp{get_random_string()}.docx'), "a")
    tempdir = tempfile.mkdtemp()
    tmp_xml_file = open(template_docx.extract("word/document.xml", tempdir))
    tempXmlStr = tmp_xml_file.read()
    tmp_xml_file.close()
    os.unlink(tmp_xml_file.name)

    for key in list(dicionario.keys()):
        value = str(dicionario.get(key)).replace("&", "&amp;")
        tempXmlStr = tempXmlStr.replace(key, value)

    tmp_xml_file = open(tempfile.mktemp(dir=settings.TEMP_DIR), "w+")
    tmp_xml_file.write(tempXmlStr)
    tmp_xml_file.close()

    media_relative_paths = []
    template_docx.extractall(tempdir, members=[name for name in template_docx.namelist() if 'word/media' in name])
    for dirpath, _, media_names in os.walk(os.path.join(tempdir, 'word/media')):
        for media_name in media_names:
            media_path = os.path.join(dirpath, media_name)
            size = os.stat(media_path).st_size
            if size == os.stat(os.path.join(settings.BASE_DIR, 'comum/static/comum/img/placeholder.png')).st_size:
                media_relative_paths.append(os.path.join('word/media', media_name))

    for arquivo in template_docx.filelist:
        if arquivo.filename != "word/document.xml" and arquivo.filename not in media_relative_paths:
            new_docx.writestr(arquivo.filename, template_docx.read(arquivo))

    new_docx.write(tmp_xml_file.name, "word/document.xml")
    if media_relative_paths and imagem_path:
        for media_relative_path in media_relative_paths:
            new_docx.write(imagem_path, media_relative_path)

    template_docx.close()
    new_docx.close()
    os.unlink(tmp_xml_file.name)
    shutil.rmtree(tempdir)
    if pdfa is not None:
        pdf_file_path = convert_docx_to_pdf(settings.TEMP_DIR, new_docx.filename, pdfa=pdfa)
        if pdf_file_path != new_docx.filename:
            os.unlink(new_docx.filename)
        return pdf_file_path
    else:
        # Caso não seja informado, deverá retornar o caminho para o arquivo DOCX processado.
        return new_docx.filename


def convert_docx_to_pdf(folder, source, timeout=None, pdfa=False):
    from comum.models import Configuracao
    my_env = os.environ.copy()
    my_env["HOME"] = settings.TEMP_DIR
    soffice = Configuracao.get_valor_por_chave('edu', 'caminho_libreoffice')
    if soffice:
        if settings.DEBUG and not os.path.exists(soffice):
            return source
        converto_to = 'pdf:writer_pdf_Export:SelectPdfVersion=1' if pdfa else 'pdf'
        args = [soffice, '--headless', '--convert-to', converto_to, '--outdir', folder, source]
        code = os.system(' '.join(args))
        if code == 0:
            return source.replace('.docx', '.pdf')
        else:
            e = Exception('Erro ao converter docx para pdf')
            capture_exception(e)
            raise e
    e = Exception('Configure o caminho do libre office na view /comum/configuracao')
    capture_exception(e)
    raise e


# Métodos e Classe utilitária para manipulação de dados para jogar para tabela e/ou gráficos
def soma(*args):
    if not args:
        return 0
    else:
        return sum(args)


def sub(*args):
    if not args:
        return 0
    else:
        total = args[0]
        for arg in args[1:]:
            total = total - arg
    return total


def mult(*args):
    if not args:
        return 0
    else:
        total = args[0]
        num_args = len(args)
        for i in range(1, num_args):
            total = total * args[i]
    return total


def div(*args):
    if not args:
        return 0
    else:
        total = args[0]
        num_args = len(args)
        for i in range(1, num_args):
            if args[i] != 0:
                total = total / args[i]
            else:
                total = 0
    return total


def percentual(a, b):
    if a == 0 or b == 0:
        return 0
    return (100.0 * a) / b


def media(*args):
    if not args:
        return 0
    else:
        return soma(*args) / float(len(args))


def transposta(ltabela):
    """
    Realiza a transpostar de uma tabela (lista de lista)
    """
    return list(map(list, zip(*ltabela)))


class Relatorio:
    @classmethod
    def get_dados_em_coluna_linha(cls, lista_de_dict, cabecalho, nome_coluna, nome_linha, nome_valor, adiciona_e_totaliza=False):
        """
        Recebe uma lista de dicionário ({'nome_coluna':'', 'nome_linha':'', 'nome_valor':0.0},)
        Converte o dicionário em uma tabela (lista de lista), onde o primeiro item é nome_linha e
        os demais são os valores correspondentes aos itens de lista_cabecalho

        lista_cabecalho é passada por referência, ela é prenchida com os valores de nome_coluna
        presentes no dicionário lista_de_dict
        """
        # Cria uma lista com os estados sem repetição
        for ditem in lista_de_dict:
            try:
                cabecalho.index(ditem[nome_coluna])
            except ValueError:
                cabecalho.append(ditem[nome_coluna])

        # Adiciona o valor para cada nome_coluna e nome_linha
        ltabela_aux = []
        for ditem in lista_de_dict:
            nomeLinha = ditem[nome_linha]
            llinha = cls._find(nomeLinha, ltabela_aux)
            nova_linha = False
            if not llinha:
                # cria uma linha vazia com len(cabecalho)+1 colunas
                llinha = [0.0] * (len(cabecalho) + 1)
                llinha[0] = nomeLinha
                nova_linha = True
            try:
                index = cabecalho.index(ditem[nome_coluna])
                llinha[index + 1] += float(ditem[nome_valor])
            except ValueError:
                pass
            if nova_linha:
                ltabela_aux.append(llinha)

        # adiciona em ltabela somente se existir produção, ou seja, ao menos um item ser diferente de zero.
        ltabela = []
        for litem in ltabela_aux:
            if any(i > 0 for i in litem[1:]):
                ltabela.append(litem)

        if adiciona_e_totaliza:
            Relatorio.adiciona_e_totaliza_coluna(ltabela)
            cabecalho.append('Total')

        return ltabela

    @classmethod
    def _find(cls, item, lista):
        obj = [valor for valor in lista if valor[0] == item]
        if obj:
            return obj[0]
        else:
            return None

    @classmethod
    def adiciona_e_totaliza_coluna(cls, ltabela, lfunctabela=None):
        """
        Adiciona uma nova coluna na tabela ltabela
        Parâmetros:
            lfunctabela : uma lista de lista, representa uma tabela com num_colunaslista
            lfunctabela: formato [funcao, 1,2], onde:
                funcao: é um ponteiro para função
                demais itens, refere-se as colunas que serão calculadas com a fórmula funcao
        """
        if ltabela:
            for linha in ltabela:
                lcoluna = []
                if lfunctabela:
                    for col in lfunctabela[1:]:
                        lcoluna.append(linha[col])

                    linha.append(round(lfunctabela[0](*lcoluna), 2))
                else:
                    for col in linha[1:]:
                        lcoluna.append(col)

                    linha.append(round(soma(*lcoluna), 2))

    @classmethod
    def adiciona_nova_coluna(cls, ltabela, lresultados, dic_values, num_colunas):
        """
        Adiciona ou edita uma coluna na tabela.

        Recebe os seguintes parâmetros:
        ltabela : uma lista de lista, representa uma tabela com num_colunaslista
        lresultados: lista a ser inserida na tabela, cada item de lresultados é uma linha na tabela
        dic_values: dicionário (chave, valor), onde chave representa a coluna (índice da nova coluna a ser inserida na ltabela)
                    e valor representa o valor (índice de lresultados[0] da célula da ltabela.
        num_colunas: é o número de colunas da tabela, istó é, o número de itens da lista.
        """
        if lresultados:
            for item in lresultados:
                llinha = cls._find(item[0], ltabela)
                nova_linha = False
                if not llinha:
                    # cria uma linha vazia com num_colunas
                    llinha = [0.0] * num_colunas
                    llinha[0] = item[0]
                    nova_linha = True
                for k, v in list(dic_values.items()):
                    # linha na tabela já existe, atualiza os valures das colunas
                    llinha[k] = float(item[v])
                if nova_linha:
                    ltabela.append(llinha)

    @classmethod
    def get_linha_total(cls, ltabela, dic_execfunc=None):
        """
        ltabela: (lista de lista)
        Recebe dic_execfunc no formato {1:soma,2:mult, 3:media}, onde a
        chave é o índice de ltabela[linha] e o valor e o ponteiro para função.
        Exemplo:
            lt = [['a',5,10,15], ['b', 2, 4, 6]]
            get_linha_total(lt,{1:media, 2:mult}), retorno = [3.5, 40, 21)
            onde:
                3.5 é a media dos itens da 1ª coluna
                40 é a multicplicação dos itens da 2ª coluna
                21 é o padrão, isto é a soma dos itens para cada coluna restante
        """
        if ltabela:
            ltabela_inversa = transposta(ltabela)
            num_colunas = len(ltabela[0])
            ltotal = [0.0] * num_colunas
            ltotal[0] = 'TOTAL'
            for icol in range(1, len(ltabela_inversa)):
                if dic_execfunc and dic_execfunc.get(icol, None):
                    execfunc = dic_execfunc.get(icol, None)
                    ltotal[icol] = execfunc(*ltabela_inversa[icol])
                else:
                    ltotal[icol] = soma(*ltabela_inversa[icol])
            return ltotal

    @classmethod
    def ordernar(cls, dados, funcao=lambda e: e[0]):
        return sorted(dados, key=funcao)


def gera_nomes(nome, separador=' '):
    tokens = to_ascii(retirar_preposicoes_nome(nome).upper()).split()
    nomes = []
    for t1 in tokens:
        for t2 in tokens:
            if not t1 == t2:
                nome = '{}{}{}'.format(t1, separador, t2)
                nomes.append(nome)
    return nomes


def procurar_arquivos_ausentes():
    for model in apps.get_models():
        print()
        print('#' * 40)
        print(model)
        print('#' * 40)
        for field in [f for f in model._meta.fields if isinstance(f, models.FileField)]:
            values_list = model.objects.exclude(**{field.attname: ''}).exclude(**{field.attname: None}).values_list('id', field.attname).order_by('id')
            for pk, filename in values_list:
                if callable(field.upload_to):
                    part1 = ''
                else:
                    part1 = settings.MEDIA_ROOT
                filename_path = os.path.join(part1, filename)
                if not os.path.exists(filename_path):
                    print(('pk', pk, 'field', field.attname, '>', filename_path))


def get_qtd_dias_por_ano(periodo_data_inicio, periodo_data_final):
    #
    # dado um período de datas, calcular a quantidade de dias por ano
    qtd_dias_por_ano = {}  # {ano: qtd, ano: qtd, ano: qtd, ...}
    for data in datas_entre(periodo_data_inicio, periodo_data_final):
        ano = data.year
        if ano not in qtd_dias_por_ano:
            qtd_dias_por_ano[ano] = 0
        qtd_dias_por_ano[ano] += 1
    return qtd_dias_por_ano


def tem_permissao_informar_erro(request):
    if not all([
        'erros' in settings.INSTALLED_APPS,
        hasattr(request, 'build_absolute_uri'),
        request.user.is_authenticated
    ]):
        return False
    return True


def respond_as_attachment(file_path, original_filename):
    fp = open(file_path, 'rb')
    response = HttpResponse(fp.read())
    fp.close()
    file_type, encoding = mimetypes.guess_type(original_filename)
    if file_type is None:
        file_type = 'application/octet-stream'
    response['Content-Type'] = file_type
    response['Content-Length'] = str(os.stat(file_path).st_size)
    if encoding is not None:
        response['Content-Encoding'] = encoding
    filename_header = 'filename*=UTF-8\'\'%s' % urllib.parse.quote(original_filename)
    response['Content-Disposition'] = 'attachment; ' + filename_header
    return response


def retira_acentos(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def HTMLEntitiesToUnicode(text):
    """Converter entidades HTML em unicode. Ex.: &amp; para &. &lt; para <."""
    text = str(BeautifulStoneSoup(text, convertEntities=BeautifulStoneSoup.ALL_ENTITIES))
    return text


def HMTLParaStringUnicode(text):
    """Converter string com tags HTML e entidades HTML em string unicode limpa."""
    tag_re = re.compile(r'(<!--.*?-->|<[^>]*>)')
    texto_unicode_com_tags = HTMLEntitiesToUnicode(text)
    # Remove well-formed tags, fixing mistakes by legitimate users
    no_tags = tag_re.sub('', texto_unicode_com_tags)
    # Clean up anything else by escaping
    ready_for_web = cgi.escape(no_tags)
    return ready_for_web


def get_values_from_choices(choice_keys, choices):
    '''
    Retorna o valor amigável de um item, ou vários itens, de um choices
    Obs: Caso você queira apenar o valor amigável de um campo do models seu usa CHOICES, basta fazer "model.get_campo_display()"

    Exemplo:

    NIVEL_ACESSO_SIGILOSO = 1
    NIVEL_ACESSO_RESTRITO = 2
    NIVEL_ACESSO_PUBLICO = 3
    NIVEL_ACESSO_CHOICES = (
        (NIVEL_ACESSO_SIGILOSO, u'Sigiloso'),
        (NIVEL_ACESSO_RESTRITO, u'Restrito'),
        (NIVEL_ACESSO_PUBLICO, u'Público'),
    )
    print get_value_from_choices(NIVEL_ACESSO_SIGILOSO, NIVEL_ACESSO_CHOICES)
    >>> Sigiloso

    print get_value_from_choices([NIVEL_ACESSO_SIGILOSO, NIVEL_ACESSO_RESTRITO], NIVEL_ACESSO_CHOICES)
    >>> [ Sigiloso, Restrito]

    :param choice_keys: um chave ou várias chaves do choices
    :param choices: choices que contém as chaves e valores

    :return: uma string caso choice_keys seja apenas uma key ou uma lista de strings caso choice_keys seja uma lista de keys.
    '''
    choices_as_dict = dict(choices)

    if type(choice_keys) is list:
        result = list()
        for key in choice_keys:
            result.append(choices_as_dict[key])
        return result
    else:
        return choices_as_dict[choice_keys]


def convert_bytes_to_strb64(bytes):
    # bytes > encode to bytes b64 > decode to string b64
    bytes_b64 = base64.b64encode(bytes)
    str_b64 = bytes_b64.decode('utf-8')
    return str_b64


def convert_strb64_to_bytes(strb64):
    # string b64 > encode to bytes b64 > decode to bytes
    bytes_b64 = strb64.encode('utf-8')
    bytes = base64.b64decode(bytes_b64)
    return bytes
