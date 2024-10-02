import base64
import csv
import io
import functools
import hashlib
import json
import logging
import marshal
import os
import pickle
import re
import sys
import tempfile
import threading
import types
import uuid
import zlib
from collections import OrderedDict
from datetime import date, datetime, timedelta
from decimal import Decimal
from difflib import SequenceMatcher
from functools import reduce, WRAPPER_ASSIGNMENTS, wraps
from itertools import chain
from operator import or_
from random import choice
from time import mktime
from urllib.parse import urlparse

import pdfkit
from django import forms
from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.template.defaultfilters import slugify
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth import get_permission_codename
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import Group, Permission
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core import validators
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.files.storage import default_storage
from django.core.signing import Signer
from django.db import models, connection
from django.db import router
from django.forms import ValidationError
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import resolve
from django.utils import termcolors
from django.utils.autoreload import StatReloader, trigger_reload
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
from sentry_sdk import capture_exception

from djtools.testutils import running_tests

try:
    from weasyprint import HTML
except ModuleNotFoundError:
    pass

from djtools.utils.tl import get_tl
from djtools.utils.response import JsonResponse, httprr
from djtools.utils.python import to_ascii
from djtools.utils.breadcrumbs import breadcrumbs_previous_url, breadcrumbs_add  # NOQA
from djtools.utils.email import send_notification

from djtools.utils.http import *  # NOQA
from djtools.utils.breadcrumbs import *  # NOQA
from djtools.utils.email import *  # NOQA
from djtools.utils.response import *  # NOQA
from djtools.utils.session import *  # NOQA
from djtools.utils.python import *  # NOQA
from djtools.utils.deprecation import *  # NOQA
from djtools.utils.database import *  # NOQA
from djtools.utils.loggingplus import *  # NOQA
from djtools.utils.serialization import *  # NOQA


logger = logging.getLogger('weasyprint')
logger.setLevel(logging.CRITICAL)


def notify_file_changed(self, path):
    if str(path).endswith('py'):
        trigger_reload(path)


if settings.DEBUG:
    StatReloader.notify_file_changed = notify_file_changed


def similaridade(a, b):
    """
    Verifica se duas sequências são similares.

    Args:
        a (iterable): sequência comparável.
        b (iterable): sequência comparável.

    Returns:
        Float, entre 0 e 1, que demonstra o grau de similaridade entre as duas sequências.
    """
    return SequenceMatcher(None, a, b).ratio()


def get_datetime_now():
    """
    Obtem a data e hora atual do servidor.

    Returns:
        timezone.now() caso seja possível importar o timezone, caso contrário, datetime.now().
    """
    try:
        from django.utils import timezone

        return timezone.now()
    except ImportError:
        import datetime

        return datetime.datetime.now()


class EnumBase(type):
    """
    Metaclasse que controi enumerações de forma automática, adicionando os atributos **choices** e **choices_flat**.

    Note:
        Esta é uma classe interna e só deve ser usada no 'Enum'.
    """

    def __new__(cls, name, bases, attrs):
        """
        Construtor do tipo que monsta os atributos **choices** e **choices_flat**.

        Args:
            name (string): nome do tipo;
            bases (list): lista das classes na herança;
            attrs (dict): dicionário com os atributos do tipo.

        Returns:
             Novo tipo.
        """
        super_new = super().__new__
        module = attrs.pop('__module__')
        new_class = super_new(cls, name, bases, {'__module__': module})
        choices, choices_flat = [], []
        for key, val in list(attrs.items()):
            if type(val) in [str, int, float]:
                choices.append([val, val])
                choices_flat.append(val)
            setattr(new_class, key, val)
        setattr(new_class, 'choices', choices)
        setattr(new_class, 'choices_flat', choices_flat)
        return new_class


class Enum(metaclass=EnumBase):
    """
    Classe "abstrata" que deve ser utilizada na construção de enumerações.

    Example::

        class MeuChoice(Enum):
            CHOICE_A = 'ChoiceA'
            CHOICE_B = 'ChoiceB'
        >>> MeuChoice.choices
        >>> [['ChoiceA','ChoiceA'], ['ChoiceB', 'ChoiceB']]
        >>> MeuChoice.choices_flat
        >>> ['ChoiceA', 'ChoiceB']

    """
    choices = None  # será modificado no __new__ de EnumBase
    choices_flat = None  # será modificado no __new__ de EnumBase


def djtools_max(*args):
    """
    Especialização da função built-in que retorna o maior valor de uma lista. Essa implementação ignora valores None.

    Args:
        args: sequência de valores a analisar.

    Returns:
        Maior valor contido na sequência.
    """
    return max(i for i in list(args) if i is not None)


def djtools_min(*args):
    """
    Especialização da função built-in que retorna o menor valor de uma lista. Essa implementação ignora valores None.

    Args:
        args: sequência de valores a analisar.

    Returns:
        Menor valor contido na sequência.
    """
    return min(i for i in list(args) if i is not None)


def silenciar(silenciar_debug=False, return_on_error=None):
    """
    Decorator que captura excessões podendo lançá-las ou não.

    Args:
        silenciar_debug (bool): indica se é para ser silenciada ou não a função;
        return_on_error (): retorno padrão para funções silenciadas.

    Returns:
        Função decorada.
    """
    def receive_function(func):
        @wraps(func, assigned=WRAPPER_ASSIGNMENTS)
        def wrapper(*args, **kwargs):
            if not silenciar_debug and settings.DEBUG:
                return func(*args, **kwargs)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                capture_exception(e)
                return return_on_error

        return wrapper

    return receive_function


def human_str(val, encoding='utf-8', blank=''):
    """
    Retorna uma representação humana para o objeto.

    Args:
        val (object): objeto a ser analisado;
        encoding (string): codificação do texto de saída;
        blank (string): valor padrão caso val não exista;

    Examples:

        human_basestring(True) -> 'Sim'
        human_basestring(False) -> 'Não'
        human_basestring(User.objects.get(id=1)) -> 'admin'
        human_basestring(None) -> ''
        human_basestring(None, blank=u'-') -> '-'
        human_basestring(u'Teste') -> 'Teste'
        human_basestring('Teste') -> 'Teste'

    Returns:
        String contendo a representação humana do objeto.
    """
    if val is None:
        val = blank
    elif not isinstance(val, str):  # Não é uma string
        if isinstance(val, bool):
            val = val and 'Sim' or 'Não'
        elif hasattr(val, 'strftime'):
            if hasattr(val, 'time'):
                try:
                    val = val.strftime('%d/%m/%Y %H:%M:%S')
                except Exception:
                    val = str(val)
            else:
                try:
                    val = val.strftime('%d/%m/%Y')
                except Exception:
                    val = str(val)
        else:
            val = str(val)
    elif isinstance(val, str) and not isinstance(val, str):
        # Assume que passou uma string na codificação correta (``encoding``)
        return val
    return val  # .encode(encoding, 'replace')


def CsvResponse(rows, name='report', attachment=True, encoding='utf-8', value_for_none='-', processo=None,
                delimiter=','):
    """
    Classe derivada do **HttpResponse** que retorna um conteúdo no formato CSV.

    Args:
        rows (list of list): Dados a serem processados;
        name (string): Nome do arquivo a ser enviado ao browser;
        attachment (bool): Indica se o conteúdo será atachado a resposta;
        encoding (string): Especifica a codificação do conteúdo;
        value_for_none (string): Valor padrão utilizado quando estiver tratando None;
        processo (object): Objeto de processamento em segundo plano;
        delimiter (string): Delimitador de campo no conteúdo gerado;

    Raises:
        ValueError: Caso o paramentro '*rows*' não sera uma lista de listas.

    Returns:
        Resposta contendo o conteúdo processado ou arquivo anexado.
    """
    if not isinstance(rows, list) or (len(rows) and not isinstance(rows[0], list)):
        raise ValueError('``rows`` must be a list of lists')
    if processo:
        response = tempfile.NamedTemporaryFile(
            mode='w', delete=False, suffix='.csv')
    else:
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s.csv"' % name
    writer = csv.writer(response, delimiter=delimiter)
    for row in rows:
        row = [human_str(i, encoding=encoding, blank=value_for_none)
               for i in row]
        writer.writerow(row)

    if processo:
        response.close()
        processo.finalize('Arquivo gerado com sucesso.',
                          '..', file_path=response.name)
    else:
        return response


charwidths = {
    '0': 262.637,
    '1': 262.637,
    '2': 262.637,
    '3': 262.637,
    '4': 262.637,
    '5': 262.637,
    '6': 262.637,
    '7': 262.637,
    '8': 262.637,
    '9': 262.637,
    'a': 262.637,
    'b': 262.637,
    'c': 262.637,
    'd': 262.637,
    'e': 262.637,
    'f': 146.015,
    'g': 262.637,
    'h': 262.637,
    'i': 117.096,
    'j': 88.178,
    'k': 233.244,
    'l': 88.178,
    'm': 379.259,
    'n': 262.637,
    'o': 262.637,
    'p': 262.637,
    'q': 262.637,
    'r': 175.407,
    's': 233.244,
    't': 117.096,
    'u': 262.637,
    'v': 203.852,
    'w': 321.422,
    'x': 203.852,
    'y': 262.637,
    'z': 233.244,
    'A': 321.422,
    'B': 321.422,
    'C': 350.341,
    'D': 350.341,
    'E': 321.422,
    'F': 291.556,
    'G': 350.341,
    'H': 321.422,
    'I': 146.015,
    'J': 262.637,
    'K': 321.422,
    'L': 262.637,
    'M': 379.259,
    'N': 321.422,
    'O': 350.341,
    'P': 321.422,
    'Q': 350.341,
    'R': 321.422,
    'S': 321.422,
    'T': 262.637,
    'U': 321.422,
    'V': 321.422,
    'W': 496.356,
    'X': 321.422,
    'Y': 321.422,
    'Z': 262.637,
    ' ': 146.015,
    '!': 146.015,
    '"': 175.407,
    '#': 262.637,
    '$': 262.637,
    '%': 438.044,
    '&': 321.422,
    '\'': 88.178,
    '(': 175.407,
    ')': 175.407,
    '*': 203.852,
    '+': 291.556,
    ',': 146.015,
    '-': 175.407,
    '.': 146.015,
    '/': 146.015,
    ':': 146.015,
    ';': 146.015,
    '<': 291.556,
    '=': 291.556,
    '>': 291.556,
    '?': 262.637,
    '@': 496.356,
    '[': 146.015,
    '\\': 146.015,
    ']': 146.015,
    '^': 203.852,
    '_': 262.637,
    '`': 175.407,
    '{': 175.407,
    '|': 146.015,
    '}': 175.407,
    '~': 291.556,
}


class FitSheetWrapper:
    """
    Tenta ajustar as columas para o tamanho máximo de qualquer valor de entrada.
    Em seu uso deve-se adicionar a planilha retornara em uma pasta de trabalho como exemplo abaixo.

    Example:

        sheet = FitSheetWrapper(book.add_sheet(sheet_name))


    Try to fit columns to max size of any entry.
    To use, wrap this around a worksheet returned from the
    workbook's add_sheet method, like follows:

        sheet = FitSheetWrapper(book.add_sheet(sheet_name))

    Note:
        A planilha continua a mesma, somente os campos com dimencionamento automático serão afetados.
    """

    def __init__(self, sheet):
        """
        Construtor.

            sheet (): planilha.
        """
        self.sheet = sheet
        self.widths = dict()

    def write(self, r, c, label='', *args, **kwargs):
        """
        Escreve dados na planilha.

        Args:
            r (int): linha que será escrita a informação;
            c (int): coluna que será escrita a informação;
            label (string): rótulo a ser escrito;
            *args (list): paramentros posicionais gerais;
            **kwargs (dict): paramentros nomeados gerais;
        """
        self.sheet.write(r, c, label, *args, **kwargs)
        width = int(FitSheetWrapper.fitwidth(label))
        if width > 65000:
            width = 65000
        elif width < 1:
            width = 1
        if width > self.widths.get(c, 0):
            self.widths[c] = width
            self.sheet.col(c).width = width

    def __getattr__(self, attr):
        """
        Sobrecarga do método para retorno de um item com base em uma chave.

            attr (string): chave para pesquisa.

        Returns:
             Item com base na chave **attr**.
        """
        return getattr(self.sheet, attr)

    def colwidth(n):
        """
        Traduz unidades naturais (humanas) para unidades de tamanho de coluna BIFF.

        Args:
            n (int): numero a ser traduzido.

        Returns:
            Inteiro que representa n na unidade BIFF
        """
        if n <= 0:
            return 0
        if n <= 1:
            return n * 456
        return 200 + n * 256

    @classmethod
    def fitwidth(cls, data, bold=False):
        """
        Tenta ajustar automaticamente a largura do valor passado para a fonte Arial com tamanho 10.

        Args:
            data (string): Valor levado em consideração no cálculo;
            bold (bool): Indica se o texto está em negrito;

        Returns:
            Inteiro com o valor da largura.
        """
        maxunits = 0
        for ndata in data.split("\n"):
            units = 220
            for char in ndata:
                if char in charwidths:
                    units += charwidths[char]
                else:
                    units += charwidths['0']
            if maxunits < units:
                maxunits = units
        if bold:
            maxunits *= 1.1
        # Don't go smaller than a reported width of 2
        return max(maxunits, 700)

    @classmethod
    def fitheight(cls, data, bold=False):
        """
        Tenta ajustar automaticamente a altura do valor passado para a fonte Arial com tamanho 10.

        Args:
            data (string): Valor levado em consideração no cálculo;
            bold (bool): Indica se o texto está em negrito;

        Returns:
            Inteiro com o valor da altura.
        """
        rowlen = len(data.split("\n"))
        if rowlen > 1:
            units = 230 * rowlen
        else:
            units = 290
        if bold:
            units *= 1.1
        return int(units)


def XlsResponse(rows, name='report', attachment=True, encoding='iso8859-1', value_for_none='-', convert_to_ascii=False,
                processo=None):
    """
    Retorna uma resposta no formato *xls*. Todos os valores valores serão convertidos com '*human_str*'.

    Args:
        rows: linhas do dado a ser processado;
        name (string): Nome do arquivo a ser anexado;
        attachment (bool): Indica se o conteúdo deverá ser um anexado;
        encoding (string): Codificação do conteúdo a ser retornado;
        value_for_none (string): Valor a ser utilizado quando estiver escrevendo um None;
        convert_to_ascii (bool): Indica se deve-se converter para o padrão **ASCII**;
        processo: Objeto que realiza o processamento em segundo plano;

    Raises:
        ValueError: caso '**rows**' não seja nem uma lista de listas e nem um dicionário de lista de listas

    Returns:
        Resposta contendo o conteúdo processado ou arquivo anexado.

    Notes:

        * O parâmetro rows deve ser uma das opções abaixo:
            - Lista de listas: Nesse caso será criada um arquivo excel e todos os dados presentes serão armazenados
              numa guia chamada 'Planilha1'. Veja o exemplo::

                rows = get_exportacao(qs_alunos,
                                      ['matricula', 'pessoa_fisica.nome', 'pessoa_fisica.cpf',],
                                      ['Matrícula', 'Nome', 'CPF',])
                return XlsResponse(rows)

            - Dicionario de lista de listas: Nesse caso será criado arquivo excel e para cada item do dicionário será
              criada uma guia com o nome da chave do item. Isto é bastante útil quando houver a nececessidade de por mais
              de uma informação num mesmo arquivo excel, separando cada informação em uma guia, conforme exemplo
              abaixo::

                rows_alunos_matriculados = get_exportacao(...
                rows_alunos_jubilados = get_exportacao(...
                rows = {'PlanilhaAM':rows_alunos_matriculados, 'PlanilhaAJ':rows_alunos_jubilados}
                return XlsResponse(rows)

        * Caso necessite que as guias sejam criadas na mesma ordem de inserção dos items no dicionário, usar a classe
          collections.OrderedDict;
    """
    import xlwt

    rows_as_list_of_lists = isinstance(rows, list) and len(
        rows) and isinstance(rows[0], list)

    rows_as_dict_of_list_of_lists = (
        isinstance(rows, dict) and len(rows) and isinstance(list(rows.values())[0], list) and len(
            list(rows.values())[0]) and isinstance(list(rows.values())[0][0], list)
    )

    if not rows_as_list_of_lists and not rows_as_dict_of_list_of_lists:
        raise ValueError(
            '``rows`` must be a "list of lists" or a "dict of list of lists"')

    # Dicionário que servirá de base para a montagem da planilha.
    dict_to_mount_excel = dict()
    if rows_as_list_of_lists:
        dict_to_mount_excel["Planilha1"] = rows
    else:
        dict_to_mount_excel = rows

    if processo:
        tmp_dir = settings.TEMP_DIR
        if not os.path.exists(tmp_dir):
            os.mkdir(tmp_dir)
        response = tempfile.NamedTemporaryFile(
            mode='w+b', dir=tmp_dir, delete=False, suffix='.xls')
    else:
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename=%s.xls' % name

    wb = xlwt.Workbook(encoding=encoding)

    # Cada item do dicionário preencherá uma guia do arquivo excel.
    for sheet_name, sheet_rows in list(dict_to_mount_excel.items()):
        # Adicinando uma guia ao arquivo excel, utilizando como nome a "key"
        # do item corrente do dicionário.
        # sheet = wb.add_sheet(sheet_name)
        sheet = FitSheetWrapper(wb.add_sheet(sheet_name))

        # Adicionando os dados da guia corrente. `sheet_rows` é uma matriz, ou seja, uma
        # lista de listas, logo `row_data` é uma lista.
        row_idx = 0
        for row_data in processo and processo.iterate(sheet_rows) or sheet_rows:
            if convert_to_ascii:
                row_data = [to_ascii(val) for val in row_data]

            # Apĺicando o método `human_str` para cada item da lista.
            # Ex: ['2107029', 'Misael Barreto', '01054377430']
            row_data = [human_str(i, encoding=encoding,
                                  blank=value_for_none) for i in row_data]

            # Preenchendo cada linha da guia corrente com os dados da lista.
            for col_idx, col in enumerate(row_data):
                sheet.write(row_idx, col_idx, label=col)
            if processo and hasattr(processo, 'next'):
                next(processo)
            row_idx += 1

    wb.save(response)
    if processo:
        response.close()
        processo.finalize('Arquivo gerado com sucesso.',
                          '..', file_path=response.name)
    else:
        return response


####################
# Autocomplete ###
####################
@login_required
@csrf_exempt
def autocomplete_view(request, app_name, class_name):
    """
    View utilizada no processamento de campos do tipo autocomplete. O uso dessa view visa minimizar o transito de
    dados na construção de formulários, para tal, relacionamentos **one to many** são carregados por demanda,
    de acordo com a necessidade dos usuários.

    Args:
        request (HttpRequest): objeto requeste;
        app_name (string): nome da aplicação que originou a requisição;
        class_name (string): nome da classe, normalemten de formulário, que originou a requisição.

    Raises:
        Exception: caso não seja possível obter o modelo contido em *app_name* e com o nome *class_name*.

    Returns:
        Queryset ou formato separado por "|".

    Note:
        É esperado que o POST contenha a chave 'q', o *'manager_name'* e opcionalmente *'force_generic_search'*, onde
        o *manager_name* é o nome do mananger a ser utilizado na pesquisa e o force_generic_search força a pesquisa em
        todos os campos do modelo.
    """
    SEARCH_FUNCTION_NAME = 'buscar'
    try:
        cls = apps.get_model(app_name, class_name)
    except Exception:
        return HttpResponse('Classe inválida!')
    data = request.method == 'POST' and request.POST or request.GET
    if cls is None:
        raise Exception('Invalid Class')
    if 'pk' in data:
        # Retorna apenas a representação unicode do objeto. É utilizado na
        # escolha do objeto via change_list do admin.
        try:
            return HttpResponse(str(cls.objects.get(pk=data['pk'])))
        except (cls.DoesNotExist, ValueError):
            return HttpResponse('')

    if 'force_generic_search' not in data and hasattr(cls, SEARCH_FUNCTION_NAME):
        args = dict(autocomplete=True)
        for key, value in list(data.items()):
            args[str(key)] = value
        return HttpResponse(cls.buscar(**args))
    else:
        readonly = 'readonly' in data

        if 'search_fields' in data:
            search_fields = [search_field.strip()
                             for search_field in data['search_fields'].split(',')]
        else:
            search_fields = None

        if 'django_filter_names' in data and 'filter_pks' in data:
            django_filter_names = data['django_filter_names'].split(',')
            filter_pks = data['filter_pks'].split(',')
            for i, elem in enumerate(filter_pks):
                if elem and django_filter_names[i].endswith('__in'):
                    filter_pks[i] = elem.split(';')
        else:
            django_filter_names = None
            filter_pks = None

        ext_combo_template = data.get('ext_combo_template')
        if ext_combo_template:
            # http://stackoverflow.com/questions/1253528/is-there-an-easy-way-to-pickle-a-python-function-or-otherwise-serialize-its-cod#answers-header
            # deserializa a função
            ext_combo_template = timeless_load_qs_query(ext_combo_template)
            code_ext_combo_template = marshal.loads(ext_combo_template)
            ext_combo_template = types.FunctionType(
                code_ext_combo_template, globals(), "some_func_name")

        args = dict(
            autocomplete_format=True,
            q=data.get('q', ''),
            control=data.get('control', None),
            manager_name=data.get('manager_name', None),
            label_value=data.get('label_value', None),
            qs_filter=data.get('qs_filter', None),
            search_fields=search_fields,
            django_filter_names=django_filter_names,
            filter_pks=filter_pks,
            ext_combo_template=ext_combo_template,
            readonly=readonly,
        )
        return HttpResponse(generic_search(cls, **args))


def generic_search(
        cls,
        q,
        autocomplete_format=True,
        manager_name=None,
        label_value=None,
        search_fields=None,
        qs_filter=None,
        split_q=True,
        control=None,
        django_filter_names=None,
        filter_pks=None,
        ext_combo_template=None,
        readonly=False,
):
    """
    Realiza a busca em modelos de maneira transparente para quem o invoca.

    Args:
        cls (object): classe relacionada com a busca;
        q (string): termo a ser pesquisado;
        autocomplete_format (bool): indica se o resultado deve ter um formato específico;
        manager_name (string): nome do manager, específico, a ser utilizado;
        label_value (string): indica o label para a busca;
        search_fields (list): lista de campos que devem ser utilizados na busca;
        qs_filter (string): string contendo um filtro simples no formato key=value;
        split_q (bool): indica se os termos contido em q devem ser separados;
        control (string): string contendo a representação do modelo filtrado da classe. Essa string está codificada;
        django_filter_names (list): lista dos filtros, extras, para realizar novo filtro no modelo;
        filter_pks (list): lista das pks associadas aos django_filter_names;
        ext_combo_template (function): função utilizada para formatar a saída, caso o argumento autocomplete_format seja verdadeiro;
        readonly (bool): indica que o campo de busca é somente leitura.

    Raises:
        Exception: caso o campo não seja readonly e o modelo passado não contenha campos a buscar.

    Returns:
        Lista contendo o resultado da busca, caso não tenha formatação essa lista será um queryset.
    """

    def get_queryset(cls, manager_name=None, control=None):
        """
        Obter um queryset com base nos dados passados.

        Args:
            cls (Model): classe base para realizar os filtros;
            manager_name (Manager): manager que deve ser utilizadom caso não seja passado é utilizado o padrão;
            control (string): string codificada contendo o queryset original.

        Returns:
            Queryset com o filtro passado através do control.
        """
        try:
            manager = manager_name and getattr(
                cls, manager_name) or cls.objects
            if control:
                queryset = manager.all()
                queryset.query = timeless_load_qs_query(control)
                return queryset
            else:
                return manager.none()
        except Exception:
            return None

    def construct_search(field_name):
        return '%s__icontains' % field_name

    def get_search_fields_alternative(cls):
        """
        Obter a lista de campos texto que serão utilizados na busca. Inicialmente é verificado se o modelo passado
        contem o atributo SEARCH_FIELDS, se não tiver é rastreado todos os campos do tipo CharField.

        Args:
            cls (Model): classe base para busca dos campos.

        Returns:
            Lista contendo os campos utilizados na pesquisa.
        """
        # Fazendo a busca por um atributo do model do tipo SearchField
        for f in cls._meta.fields:
            if f.__class__.__name__ == 'SearchField':
                return [f.name]

        # Fazendo a busca de um atributo estático do model chamado SEARCH_FIELDS
        if hasattr(cls, 'SEARCH_FIELDS'):
            return cls.SEARCH_FIELDS

        # Em último caso será feito uma varredua por todos os atributos do modelo do tipo texto.
        from django.db.models import CharField

        char_fields = [
            x.name for x in cls._meta.fields if isinstance(x, CharField)]
        return char_fields

    search_fields = search_fields or get_search_fields_alternative(cls)

    # Caso não haja campos para busca e o componente não esteja 'read_only' então será lançada uma exceção.
    if not search_fields and not readonly:
        raise Exception(
            'Autocomplete is not readonly and the class %s don\'t have a attribute SearchField, a '
            'SEARCH_FIELDS static constant or CharFields attributes, and you don\'t pass explicity a '
            '\'search_field\' param. Choose one of options or change it to readonly.' % cls.__name__
        )

    qs = get_queryset(cls, manager_name, control)
    if not qs:
        return ''
    qs = qs.all()
    depends = {}
    if django_filter_names and filter_pks:
        list_depends = list(zip(django_filter_names, filter_pks))
        for item in list_depends:
            if item[0] and item[1]:
                depends[item[0]] = item[1]
        if depends:
            qs = qs.filter(**depends).distinct()

    # Se o componente não estiver trabalhando no modo readonly, então
    # é montado o filtro aplicando os campos definidos em search_fields
    # com cada palavra presente na string digitada no componente.
    if not readonly:
        words = split_q and q.split() or [q]
        for word in words:
            or_queries = [models.Q(
                **{construct_search(str(field_name)): word}) for field_name in search_fields]
            qs = qs.filter(reduce(or_, or_queries))

    if qs_filter:
        k, v = qs_filter.split('=')
        if k.endswith('__in'):
            v = v.split(',')
        qs = qs.filter(**{str(k): v})
    if hasattr(qs, 'autocomplete'):
        qs = qs.autocomplete()
    if autocomplete_format:
        out = []
        for obj in qs[:20]:  # Limitar a 20
            row = []
            if ext_combo_template:
                row.append(ext_combo_template(obj).replace(
                    '|', '/').replace('\n', ' '))
            if hasattr(obj, 'get_ext_combo_template'):
                row.append(obj.get_ext_combo_template().replace(
                    '|', '/').replace('\n', ' '))
            row.append(eval_attr(obj, label_value or '__str__').replace(
                '|', '/').replace('\n', ' '))
            row.append(str(obj.pk))
            out.append('|'.join(row))
        return '\n'.join(out)
    else:
        return qs


@csrf_exempt
def json_view(request, app_name, class_name):
    """
    View genérica que retorna o conteúdo de um modelo no formato *JSON*.

    Args:
        request (HttpRequest): objeto request da requisição;
        app_name (string): string contendo o nome da aplicação do modelo;
        class_name (string): string contendo o nome do modelo.

    Raises:
        Exception se o conjunto app_name.class_name não representar um modelo existente.

    Returns:
        Conteúdo formatado no padrão *JSON*

    Notes:
        É utilizado o generic_search_json que tem o funcionamento semelhante ao generic_search, com isso, os paramentros
        devem ser passados via request.POST ou request.GET, itens esperados: 'q', manager_name', 'force_generic_search'.

    """
    PUBLIC_DATA = [
        ('comum', 'registroemissaodocumento'),
        ('processo_eletronico', 'tipoprocesso'),
    ]
    SEARCH_FUNCTION_NAME = 'buscar_json'
    if not request.user.is_authenticated and (app_name, class_name) not in PUBLIC_DATA:
        return HttpResponse('Usuário não autenticado')
    try:
        cls = apps.get_model(app_name, class_name)
    except Exception:
        return HttpResponse('Classe inválida!')

    data = request.method == 'POST' and request.POST or request.GET
    if cls is None:
        raise Exception('Invalid Class')

    if 'force_generic_search' not in data and hasattr(cls, SEARCH_FUNCTION_NAME):
        args = dict(autocomplete=True)
        for key, value in list(data.items()):
            args[str(key)] = value
        return JsonResponse(cls.buscar_json(**args))
    else:
        readonly = 'readonly' in data

        if 'search_fields' in data:
            search_fields = [search_field.strip()
                             for search_field in data['search_fields'].split(',')]
        else:
            search_fields = None

        if 'filter_pks' in data:
            filter_pks = json.loads(data['filter_pks'])
        else:
            filter_pks = None

        page = int(data.get('page', 1))

        ext_combo_template = data.get('ext_combo_template')
        if ext_combo_template:
            # http://stackoverflow.com/questions/1253528/is-there-an-easy-way-to-pickle-a-python-function-or-otherwise-serialize-its-cod#answers-header
            # deserializa a função
            ext_combo_template = timeless_load_qs_query(ext_combo_template)
            code_ext_combo_template = marshal.loads(ext_combo_template)
            ext_combo_template = types.FunctionType(
                code_ext_combo_template, globals(), "some_func_name")

        form_filters = []
        for key in data.keys():
            if key.startswith('form_filter__'):
                if data[key]:
                    form_filters.append((key[13:], data[key]))

        args = dict(
            q=data.get('q', ''),
            control=data.get('control', None),
            manager_name=data.get('manager_name', None),
            label_value=data.get('label_value', None),
            qs_filter=data.get('qs_filter', None),
            search_fields=search_fields,
            filter_pks=filter_pks,
            ext_combo_template=ext_combo_template,
            readonly=readonly,
            page=page,
            form_filters=form_filters
        )
        return JsonResponse(generic_search_json(cls, **args))


def generic_search_json(cls, q,
                        manager_name=None,
                        label_value=None,
                        search_fields=None,
                        qs_filter=None,
                        split_q=True,
                        control=None,
                        filter_pks=None,
                        ext_combo_template=None,
                        readonly=False,
                        page=None,
                        form_filters=None
                        ):
    """
    Realiza a busca em modelos de maneira transparente para quem o invoca.

    Args:
        cls (object): classe relacionada com a busca;
        q (string): termo a ser pesquisado;
        manager_name (string): nome do manager, específico, a ser utilizado;
        label_value (string): indica o label para a busca;
        search_fields (list): lista de campos que devem ser utilizados na busca;
        qs_filter (string): string contendo um filtro simples no formato key=value;
        split_q (bool): indica se os termos contido em q devem ser separados;
        control (string): string contendo a representação do modelo filtrado da classe. Essa string está codificada;
        filter_pks (list): lista das pks associadas aos django_filter_names;
        ext_combo_template (function): função utilizada para formatar a saída, caso o argumento autocomplete_format seja verdadeiro;
        readonly (bool): indica que o campo de busca é somente leitura;
        page ():
        form_filters: a lista de tuplas contendo chave e valor. Ex: [('setor__uo', 1)]
    Raises:
        Exception: não seja encontrado nenhum campo para busca e não seja indicado que é readonly.

    Returns:
        Lista contendo o resultado da busca, caso não tenha formatação essa lista será um queryset.
    """

    def get_queryset(cls, manager_name=None, control=None):
        """
        Obter um queryset com base nos dados passados.

        Args:
            cls (Model): classe base para realizar os filtros;
            manager_name (Manager): manager que deve ser utilizadom caso não seja passado é utilizado o padrão;
            control (string): string codificada contendo o queryset original.

        Returns:
            Queryset com o filtro passado através do control.
        """
        manager = manager_name and getattr(cls, manager_name) or cls.objects
        if control:
            queryset = manager.all()
            try:
                queryset.query = timeless_load_qs_query(control)
            except Exception:
                return manager.none()
        else:
            return manager.none()
        return queryset

    def construct_search(field_name):
        """
        Constroi a string de busca para o campo passado.

        Args:
            field_name (string): nome do campo.

        Returns:
            String contendo a busca no formato: **campo__icontains**
        """
        return '%s__icontains' % field_name

    def get_search_fields_alternative(cls):
        """
        Obtem a lista de campos a pesquisar de um modelo. Os campos utilizados segue a seguinte lógica:
            1 - Busca por campos do tipo *SearchFields*;
            2 - Verifica a existência do atributo *SEARCH_FIELDS* no modelo;
            3 - Todos os campos do tipo CharField.

        Args:
            cls (Model): modelo base para busca dos campos para pesquisa.

        Returns:
             Lista contendo o nome dos campos para busca.
        """
        # Fazendo a busca por um atributo do model do tipo SearchField
        for f in cls._meta.fields:
            if f.__class__.__name__ == 'SearchField':
                return [f.name]

        # Fazendo a busca de um atributo estático do model chamado SEARCH_FIELDS
        if hasattr(cls, 'SEARCH_FIELDS'):
            return cls.SEARCH_FIELDS

        # Em último caso será feito uma varredua por todos os atributos do modelo do tipo texto.
        from django.db.models import CharField

        char_fields = [
            x.name for x in cls._meta.fields if isinstance(x, CharField)]
        return char_fields

    search_fields = search_fields or get_search_fields_alternative(cls)

    # Caso não haja campos para busca e o componente não esteja 'read_only' então será lançada uma exceção.
    if not search_fields and not readonly:
        raise Exception(
            'Autocomplete is not readonly and the class %s don\'t have a attribute SearchField, a '
            'SEARCH_FIELDS static constant or CharFields attributes, and you don\'t pass explicity a '
            '\'search_field\' param. Choose one of options or change it to readonly.' % cls.__name__
        )

    qs = get_queryset(cls, manager_name, control).all()
    if filter_pks:
        filters = {}
        for key, value in list(filter_pks.items()):
            if value:
                if key.endswith('__in'):
                    if ';' in value:
                        filters[key] = value.split(';')
                    elif ',' in value:
                        filters[key] = value.split(',')
                    else:
                        filters[key] = [value]
                else:
                    filters[key] = value
        if filters:
            qs = qs.filter(**filters).distinct()

    # Se o componente não estiver trabalhando no modo readonly, então
    # é montado o filtro aplicando os campos definidos em search_fields
    # com cada palavra presente na string digitada no componente.
    if not readonly:
        words = split_q and q.split() or [q]
        for word in words:
            or_queries = [models.Q(**{construct_search(str(field_name)): word})
                          for field_name in search_fields if word]
            if or_queries:
                qs = qs.filter(reduce(or_, or_queries))

    if qs_filter:
        k, v = qs_filter.split('=')
        if k.endswith('__in'):
            v = v.split(',')
        qs = qs.filter(**{str(k): v})

    if form_filters:
        for k, v in form_filters:
            qs = qs.filter(**{k: v})

    return generate_autocomplete_dict(qs, page, label_value, ext_combo_template)


def generate_autocomplete_dict(qs, page, label_value=None, ext_combo_template=None, ext_combo_template_text=None):
    """
    Gera um dicionário contendo os itens de um autocomplete e a quantidade de registros.

    Notes:
        O parametro *ext_combo_template* transforma o item em formato HTML e o ext_combo_template_text transforma o item em texto simples.
    """
    items = []
    for obj in qs[20 * page - 20: 20 * page]:  # Limitar a 20
        row = {'id': obj.id}
        str_text = eval_attr(obj, label_value or '__str__').replace(
            '|', '/').replace('\n', ' ')
        row['html'] = str_text
        row['text'] = str_text

        if ext_combo_template:
            row['html'] = ext_combo_template(
                obj).replace('|', '/').replace('\n', ' ')
        elif hasattr(obj, 'get_ext_combo_template'):
            if hasattr(obj.get_ext_combo_template, '__call__'):
                row['html'] = obj.get_ext_combo_template().replace(
                    '|', '/').replace('\n', ' ')
            else:
                row['html'] = obj.get_ext_combo_template.replace(
                    '|', '/').replace('\n', ' ')

        if ext_combo_template_text:
            row['text'] = ext_combo_template_text(obj)
        elif hasattr(obj, 'get_ext_combo_template_text'):
            row['text'] = obj.get_ext_combo_template_text()

        items.append(row)
    return {'total': qs.count(), 'items': items}

################
# Autocomplete #
################


def cache_queryset(queryset, keys, value=None):
    """
    Cria cache da queryset, com isso, consultas repetidas podem ser evitadas.

    Args:
        queryset (Queryset): queryset que deve ser usado na geração da cache;
        keys (list): lista com as chaves para armazenamento da cache, podendo ser 1 ou 2 itens;
        value (bool): indica se deve-se colocar em cache o objeto ou seu valor.

    Raises:
        ValueError caso a lista *keys* conter mais que 2 itens.

    Returns:
        Dict contendo o cache do queryset.
    """

    if isinstance(keys, str):
        keys = [keys]
    if len(keys) > 2:
        raise ValueError('``keys`` size limit is 2.')

    cache = dict()

    if len(keys) == 1:
        key = keys[0]
        queryset = queryset.only(key)
        for obj in queryset:
            key_val = str(getattr(obj, key))
            cache[key_val] = value and getattr(obj, value) or obj

    elif len(keys) == 2:
        key1, key2 = keys
        queryset = queryset.only(key1, key2)
        for obj in queryset:
            key_val1 = str(getattr(obj, key1))
            if key_val1 not in cache:
                cache[key_val1] = dict()
            key_val2 = str(getattr(obj, key2))
            cache[key_val1][key_val2] = value and getattr(obj, value) or obj

    return cache


#################
# ChainedSelect #
#################
@login_required
@csrf_exempt
def chained_select_view(request, app_name, class_name):
    """
    View utilizada para gerar dependência entre items de form do tipo select.

    Args:
        request (HttpRequest): objeto request da requisição;
        app_name (string): nome da aplicação que contem a classe de modelo;
        class_name (string): nome da classe de modelo.

    Returns:
        *JsonResponse* com a lista de id, label dos itens contidos em **app_name.class_name**

    Notes:
        As chaves: django_filter_names, filter_pks, control, label, qs_filter, qs_filter_params_map podem ser passados
        via POST/GET.
    """
    cls = apps.get_model(app_name, class_name)
    data = request.POST or request.GET
    label = data.get('label')
    control = data.get('control')

    qs = cls.objects.all()
    if control:
        qs.query = timeless_load_qs_query(control)

    if 'django_filter_names' in data and 'filter_pks' in data:
        django_filter_names = data['django_filter_names'].split(',')
        filter_pks = data['filter_pks'].split(',')
        for i, elem in enumerate(filter_pks):
            if elem and django_filter_names[i].endswith('__in'):
                filter_pks[i] = elem.split(';')
    else:
        django_filter_names = None
        filter_pks = None

    depends = {}
    if django_filter_names and filter_pks:
        list_depends = list(zip(django_filter_names, filter_pks))
        for item in list_depends:
            if item[0] and item[1]:
                depends[item[0]] = item[1]
        if depends:
            qs = qs.filter(**depends).distinct()

    qs_filter = data.get('qs_filter', None)

    if qs_filter:
        filters = {}
        qs_filters = qs_filter.split(',')
        for qs_filter in qs_filters:
            k, v = qs_filter.split('=')
            k = k.strip()
            v = v.strip()
            if v == 'False':
                v = False
            elif v == 'True':
                v = True
            else:
                qs_filter_value = data.get(
                    'qs_filter_params_map[%s]' % v, None)
                if qs_filter_value:
                    v = qs_filter_value
            filters[k] = v

        qs = qs.filter(**filters)

    return JsonResponse(list(qs.distinct().values('id', label)))


def user_has_one_of_perms(user, perms):
    """
    Verifica se um usuário tem ao menos uma das permissões passadas.

    Args:

        user (User): objeto do usuário a ser testado;
        perms (list): lista contendo as permissões a testar.

    Returns:
        True se o usuário tiver alguma das permissões passadas.

    """
    for perm in perms:
        if user.has_perm(perm):
            return True
    return False


def get_search_field(model_class):
    """
    Obtem o campo do tipo *SearchField* contida no modelo passado.

    Args:
        model_class (Model): classe do modelo.

    Returns:
        ModelField se foi definido um campo SearchField no modelo, caso contrário *None* é retornado.
    """
    for f in model_class._meta.fields:
        if f.__class__.__name__ == 'SearchField':
            return f
    return None


def documento(tipo_para_verificacao=None, landscape=False, validade=None, enumerar_paginas=True, pdf_response=True,
              modelo=None, forcar_recriacao=False):
    """
    Decorator utilizado para que possibilite a conversão da função/view no padrão **PDF**.

    Args:
        tipo_para_verificacao ():
        landscape ():
        validade ():
        enumerar_paginas ():
        pdf_response ():
        modelo ():
        forcar_recriacao ():

    Returns:
        Função decorada.
    """

    def receive_function(function):
        @wraps(function, assigned=WRAPPER_ASSIGNMENTS)
        def receive_function_args(request, *args, **kwargs):
            RegistroEmissaoDocumento = apps.get_model(
                'comum', 'RegistroEmissaoDocumento')
            response = function(request, *args, **kwargs)
            pk = None
            if tipo_para_verificacao:
                pk = kwargs.get('pk')
                if not pk:
                    response.headers['location'] = (
                        'Location', breadcrumbs_previous_url(request))
                    return response

            if response.headers['content-type'] == ('Content-Type', 'application/pdf'):
                return response

            if type(response) == HttpResponseRedirect:
                if response.headers['location'] == request.path:
                    response.headers['location'] = breadcrumbs_previous_url(
                        request)
                return response

            if 'html' in request.GET:
                return response

            html = response.content.decode('utf-8')

            string_paginacao = ''
            if not enumerar_paginas:
                html = html.replace('@bottom-right', '')

            data_emissao = datetime.now()
            if validade and tipo_para_verificacao not in ('Pesquisa', 'Extensão'):
                data_validade = data_emissao + timedelta(validade)
                msg_validade = '<strong>Data de Validade</strong>: %s<br>' % data_validade.strftime(
                    '%d/%m/%Y')
            else:
                data_validade = None
                msg_validade = ''

            codigo_verificador = hashlib.sha1(
                '{}{}{}'.format(request.user.pk, data_emissao, settings.SECRET_KEY).encode('utf-8')).hexdigest()
            url_suap = settings.SITE_URL
            msg = ''
            dir_name = 'comum/registroemissaodocumento/documento/{}/{}'.format(data_emissao.year, str(data_emissao.month).zfill(2))
            file_name = '{}/{}.pdf'.format(dir_name, codigo_verificador)
            if tipo_para_verificacao:
                if tipo_para_verificacao == 'Certificado ENEM':
                    msg = '''
                        <br/><br/>
                        <table>
                            <tr>
                                <td></td>
                                <td style="width: 300px; border:1px solid #ccc; font-size:18px; text-align: center; margin:0; padding: 10px 0; line-height:130%;">
                                    Código para autenticação: <br/>
                                    <strong>{}</strong>
                                </td>
                                <td></td>
                            </tr>
                        </table>
                        <br/>
                        <div style="text-align:center; font-size:14px;">
                            Este documento foi emitido pelo SUAP. Para comprovar sua autenticidade, acesse
                            <strong><a href="{}/comum/autenticar_documento/">{}/comum/autenticar_documento/</a>.</strong> <br/>
                            <strong>Tipo de Documento:</strong> {} <br/>
                            <strong>Data da Emissão:</strong> {}
                        </div>
                    '''.format(
                        codigo_verificador[0:6],
                        url_suap,
                        url_suap,
                        tipo_para_verificacao,
                        data_emissao.strftime('%d/%m/%Y'),
                    )
                else:

                    if request.GET.get('dados_assinatura'):
                        assinaturas_html = []
                        dados_assinatura = json.loads(
                            request.GET.get('dados_assinatura'))
                        for dado_assinatura in dados_assinatura:
                            assinaturas_html.append(
                                '<li><strong>{}</strong> ({}), em <strong>{}</strong> com chave <strong>{}</strong>.</li>'.format(
                                    dado_assinatura['nome'], dado_assinatura['matricula'], dado_assinatura['data'], dado_assinatura['chave'],
                                )
                            )
                        url_simples = RegistroEmissaoDocumento.url_autenticacao(
                            tipo_para_verificacao, data_emissao, codigo_verificador)
                        url_completa = RegistroEmissaoDocumento.url_autenticacao(
                            tipo_para_verificacao, data_emissao, codigo_verificador, completa=True)
                        qrcode = RegistroEmissaoDocumento.qrcode(url_completa)
                        msg = '''
                        <div class="assinaturas">
                            <div>
                                <h3>Documento assinado eletronicamente por:</h3>
                                <ul>
                                    {}
                                </ul>
                            </div>
                            <div class="qrcode">
                                <img width="20px" src="data:image/png;base64,{}" alt="QR code do documento" />
                                Este documento foi emitido pelo SUAP. Para comprovar sua autenticidade, faça a leitura do QrCode ao lado ou acesse
                                {} e informe os dados a seguir.<br/>
                                <strong>Tipo de Documento:</strong> {} <br/>
                                <strong>Data da Emissão:</strong> {} <br/>
                                <strong>Código de Autenticação:</strong> {}
                            </div>
                        </div>
                        '''.format(''.join(assinaturas_html), qrcode, url_simples, tipo_para_verificacao, data_emissao.strftime('%d/%m/%Y'), codigo_verificador[0:6])
                    else:
                        msg = '''
                            <footer>
                                <div align="center" style="text-align:center; font-size:8pt;">{}<br> Este documento foi emitido pelo SUAP. Para comprovar sua autenticidade, acesse
                                    <strong>{}/comum/autenticar_documento/</strong><br> <strong>Código de Autenticação:</strong> {}
                                    - <strong>Tipo:</strong> {} - <strong>Data da Emissão:</strong> {}
                        '''.format(
                            string_paginacao,
                            url_suap,
                            codigo_verificador[0:6],
                            tipo_para_verificacao,
                            data_emissao.strftime('%d/%m/%Y')
                        )

                        if data_validade:
                            complemento = (
                                '''
                                - %s
                                    </div>
                                </footer>
                                '''
                                % msg_validade
                            )
                        else:
                            complemento = '''
                                </div>
                            </footer>

                            '''
                        msg = msg + complemento
                if tipo_para_verificacao == 'Extensão':
                    diretorio = 'projetos/certificados/'
                    file_name = os.path.join(diretorio, '%s.pdf' % codigo_verificador)
                elif tipo_para_verificacao == 'Pesquisa':
                    diretorio = 'pesquisa/declaracoes/'
                    file_name = os.path.join(diretorio, '%s.pdf' % codigo_verificador)
            tmp = tempfile.NamedTemporaryFile(mode='w+b')
            html = html.replace('</body>', '{}</body>'.format(msg))

            if landscape == True:
                html = html.replace('a4 portrait', 'a4 landscape')
                html = html.replace('logo_if_portrait', 'logo_if_landscape')

            try:
                HTML(string=html, base_url=request.build_absolute_uri()
                     ).write_pdf(tmp.name)
            except Exception as error:
                html_error = '''<p>Ocorreu um erro ao gerar o PDF.</p>
                    <p>Evite <b>copiar</b> e <b>colar</b> texto com formatação do <b>Microsoft Word</b>.</p>
                    <p>Revise os campos preenchidos para gerar o documento e caso não consiga gerar o arquivo corretamente abra um chamado na Central de Serviços da Tecnologia da Informação anexando este PDF
                     e informando a URL desta página.</p>
                    <p> <b>Erro</b>: {}</p>
                '''.format(
                    error
                )
                pdfkit.from_string(html_error, tmp.name)
            content = tmp.read()

            if tipo_para_verificacao:
                tipo_objeto = modelo and ContentType.objects.get_for_model(
                    apps.get_model(modelo)) or None
                qs_registro = RegistroEmissaoDocumento.objects.filter(tipo=tipo_para_verificacao,
                                                                      tipo_objeto=tipo_objeto, modelo_pk=pk, cancelado=False)
                if not qs_registro or validade or settings.DEBUG or forcar_recriacao:
                    registro = RegistroEmissaoDocumento()
                    registro.tipo = tipo_para_verificacao
                    registro.data_emissao = data_emissao
                    registro.codigo_verificador = codigo_verificador
                    registro.data_validade = data_validade
                    registro.modelo_pk = pk
                    registro.tipo_objeto = tipo_objeto
                    file_obj = default_storage.save(file_name, io.BytesIO(content))
                    registro.documento = file_obj
                    registro.save()
                else:
                    registro = qs_registro[0]
                return pdf_response and registro.as_pdf_response() or registro
            else:
                return HttpResponse(content, content_type='application/pdf')

        return receive_function_args

    return receive_function


def sync_groups_and_permissions(data, descricoes, managers):
    """
    Realiza a sincronização dos grupos e permissões com base em um dicionário passado.

    Args:

        data (dict): dicionário contendo os grupos e suas permissões.

    Raises:

        ValueError quando o formato das pemissões está errado.
        Permission.DoesNotExist quando uma permissão não existe.

    Notes:

        Caso seja passado grupos não existentes/cadastrados, esses serão cadastrados.

    Examples:
        Formato do "**data**"::

            {
                '<nome_grupo>: [
                    'app_label.modelo.permissão',
                ]
            }

    """

    def get_perm(p):
        """
        Obtem o objeto da permissão passada.

        Args:
            p (string): permissão a ser pesquisada.
        ``p`` format: '<ct_app_label>.<ct_model>.<p_codename>'
        """
        try:
            ct_app_label, ct_model, p_codename = p.split('.')
        except ValueError:
            raise ValueError(
                'Value must be in format "<ct_app_label>.<ct_model>.<p_codename>". Got "%s"' % p)
        try:
            return Permission.objects.get(content_type__app_label=ct_app_label, content_type__model=ct_model,
                                          codename=p_codename)
        except Permission.DoesNotExist:
            if ct_app_label not in settings.INSTALLED_APPS:
                return None
            modelo = apps.get_model(ct_app_label, ct_model)
            if p_codename in ['{}_{}'.format(permission, ct_model) for permission in modelo._meta.default_permissions]:
                return Permission.objects.get_or_create(
                    content_type=ContentType.objects.get_for_model(modelo), codename=p_codename,
                    defaults={'name': 'Can view {}'.format(
                        modelo._meta.verbose_name)}
                )[0]
            raise Permission.DoesNotExist(
                'Permission "%s" does not exist.' % p)

    for group_name, perms in list(data.items()):
        group, created = Group.objects.get_or_create(name=group_name)
        if descricoes.get(group_name):
            from comum.models import GroupDetail
            for app, descricao in descricoes.get(group_name).items():
                GroupDetail.objects.update_or_create(group=group, app=app, defaults={
                                                     'descricao': descricao, 'app_manager': managers.get(group_name)})
        for p in perms:
            try:
                perm = get_perm(p)
                if perm:
                    group.permissions.add(perm)
            except Permission.DoesNotExist as e:
                print(e)

        codename = 'is_{}'.format(slugify(group.name).replace('-', '_'))
        content_type = ContentType.objects.get_for_model(get_user_model())
        if not group.name.endswith('_administrador'):
            perm = Permission.objects.filter(codename=codename, content_type=content_type).first()
            if not perm:
                perm = Permission.objects.create(codename=codename, content_type=content_type, name=group.name)
            group.permissions.add(perm)


def user_has_perm_or_without_request(perm, user=None):
    """
    Testa se o usuário tem a permissão caso haja um request no threadlocals.

    Args:
        perm ():
        user (User):

    Returns:
        *True* se existir um request.

    Note:
        Útil para ser utilizado no modelo, onde não se tem o request e também quando se deseja que quando não haja
        usuário logado seja "*True*" (exemplo: chamar função no shell do Django).
    """
    user = user or get_tl().get_user()
    if not user:
        return True
    return user.has_perm(perm)


def group_required(group, login_url=None, raise_exception=True):
    """
    Decora uma função para que seja testado se o usuário pertence ao grupo passado.

    Args:
        group (string): nome do grupo a testar;
        login_url (string): url para tela de login;
        raise_exception (bool): indica se é para disparar uma exceção se necessário;

    Raises:
        PermissionDenied caso o usuário não tenha permissão de acesso.

    Returns:
        Função decorada.
    """
    """Must be used as decorator."""

    def _in_group(user, group):
        from djtools.templatetags.filters import in_group

        allowed = in_group(user, group)
        # In case the 403 handler should be called raise the exception
        if not allowed and raise_exception:
            raise PermissionDenied
        # As the last resort, show the login form
        return allowed

    return user_passes_test(lambda u: _in_group(u, group), login_url=login_url)


def permission_required(perms, login_url=None, raise_exception=True, logic_operator='or'):
    """
    Decoreito que especializa o **django.contrib.auth.decorators.permission_required** para chechar se o usuário pelo
    menos uma das permissões passadas.

    Args:
        perms (list ou string): lista contendo as permissões a serem testas;
        login_url (string): url para a tela de login;
        raise_exception (bool): indica se é para disparar uma exceção se necessário;
        logic_operator (string): operador lógico para executar em casa permissão, 'or' e 'and'.

    Raises:
        TypeError caso perms não seja uma lista ou uma string.
        PermissionDenied caso o usuário não passe nos testes da permissão.

    Returns:
        Função decorada.

    Note:
        Caso perms seja uma string ela será separada utilizando delimitador a virgula.
    """

    def check_perms(user):

        or_logic_operator = True
        allowed = False
        if logic_operator.lower() == "and":
            or_logic_operator = False
            allowed = True

        def perform_logical_operation(value):
            if or_logic_operator:
                return allowed | value
            return allowed & value

        try:
            from collections.abc import Iterable
        except ImportError:  # Python 2.7 compatibility
            from collections import Iterable

        # First check if it's instance of basestring because basestring is also iterable
        # is also iterable
        if isinstance(perms, str):
            perm_list = [p.strip() for p in perms.split(',')]
        elif isinstance(perms, Iterable):
            perm_list = [p.strip() for p in perms]
        else:
            raise TypeError(
                'The first parameter must be a basestring or an iterable')

        if not user.is_authenticated:
            return False

        # First check if the user has the permission (even anon users)
        # permissions = perms.replace(',', 'or')
        # logging.info("PDP: check if %s has the permissions: %s" % (user, perms))
        for perm in perm_list:
            if user.has_perm(perm):
                allowed = perform_logical_operation(True)
            else:
                allowed = perform_logical_operation(False)

        # In case the 403 handler should be called raise the exception
        if not allowed and raise_exception:
            raise PermissionDenied

        return allowed

    return user_passes_test(check_perms, login_url=login_url)


###############################
# django.contrib.auth helpers #
###############################


def get_add_permission_for_model(model):
    """
    Obtem a string da permissão de add para um modelo.

    Args:
        model (Model): modelo a gerar a permissão.

    Returns:
        String com a permissão solicitada.
    """
    return model._meta.app_label + '.' + get_permission_codename('add', model._meta)


def get_change_permission_for_model(model):
    """
    Obtem a string da permissão de edit para um modelo.

    Args:
        model (Model): modelo a gerar a permissão.

    Returns:
        String com a permissão solicitada.
    """
    return model._meta.app_label + '.' + get_permission_codename('change', model._meta)


def get_view_permission_for_model(model):
    """
    Obtem a string da permissão de view para um modelo.

    Args:
        model (Model): modelo a gerar a permissão.

    Returns:
        String com a permissão solicitada.
    """
    return model._meta.app_label + '.' + get_permission_codename('view', model._meta)


def get_delete_permission_for_model(model):
    """
    Obtem a string da permissão de delete para um modelo.

    Args:
        model (Model): modelo a gerar a permissão.

    Returns:
        String com a permissão solicitada.
    """
    return model._meta.app_label + '.' + get_permission_codename('delete', model._meta)


def has_add_permission(model, user=None):
    """
    Verifica se o usuário tem permissão de 'add' para o modelo passado.

    Args:
        model (Model): modelo a verificar permissão;
        user (User): usuário a testar permissão.

    Returns:
        True se o usuário tiver permissão de 'add'.
    """
    user = user or get_tl().get_user()
    if not user:
        return False
    return user.has_perm(get_add_permission_for_model(model))


def has_view_permission(model, obj=None, user=None):
    """
    Verifica se o usuário tem permissão de 'view' para o modelo passado.

    Args:
        model (Model): modelo a verificar permissão;
        user (User): usuário a testar permissão.

    Returns:
        True se o usuário tiver permissão de 'view'.
    """
    user = user or get_tl().get_user()
    if not user:
        return False
    if model is None and obj:
        model = obj.__class__

    if not user.has_perm(get_view_permission_for_model(model)) and not user.has_perm(get_change_permission_for_model(model)):
        return False
    if hasattr(obj, 'can_view'):
        return obj.can_view(user=user)
    return True


def has_change_permission(model, obj=None, user=None):
    """
    Verifica se o usuário tem permissão de 'change' para o modelo passado.

    Args:
        model (Model): modelo a verificar permissão;
        obj (Objeto): objeto para verificar se tem permissão;
        user (User): usuário a testar permissão.

    Returns:
        True se o usuário tiver permissão de 'change'.
    """
    user = user or get_tl().get_user()
    if not user:
        return False
    if model is None and obj:
        model = obj.__class__

    if not user.has_perm(get_change_permission_for_model(model)):
        return False
    if hasattr(obj, 'can_change'):
        return obj.can_change(user=user)
    return True


def has_delete_permission(model=None, obj=None, user=None):
    """
    Verifica se o usuário tem permissão de 'delete' para o modelo passado ou para o objeto.

    Args:
        model (Model): modelo a verificar permissão;
        obj (Objeto): objeto para verificar se tem permissão;
        user (User): usuário a testar permissão.

    Returns:
        True se o usuário tiver permissão de 'delete'.

    Note:
        Além das permissões normais é verificado se foi implementado o método can_delete(user) no modelo, se isso
        ocorrer o método é invocado também.
    """
    user = user or get_tl().get_user()
    if not user:
        return False
    if model is None and obj:
        model = obj.__class__

    if not user.has_perm(get_delete_permission_for_model(model)):
        return False
    if hasattr(obj, 'can_delete'):
        return obj.can_delete(user=user)
    return True


def get_admin_model_url(model, sufix=None):
    """
    Obtem a **URL** de acesso a um admin baseando-se no modelo passado.

    Args:
        model (Model): modelo base bara gerar a **URL**;
        sufix (bool): indica se deve-se colocar '/' ao final da **URL**.

    Returns:
        String com a **URL** de acesso ao admin do modelo.
    """
    assert sufix in [None, 'add']
    base_url = '/admin/%(app)s/%(model)s/'
    if sufix:
        base_url += sufix + '/'
    params = dict(app=model._meta.app_label, model=model._meta.model_name)
    return base_url % params


def get_admin_object_url(obj):
    """
    Obtem a **URL** de acesso edição do objeto pelo admin.

    Args:
        obj (Model): objeto base para edição.

    Returns:
        A **URL** para edição do objeto no admin.
    """
    base_url = get_admin_model_url(obj.__class__)
    return base_url + str(obj.pk) + '/'


def get_admin_view_object_url(obj):
    """
    Obtem a **URL** de acesso visualização do objeto pelo admin.

    Args:
        obj (Model): objeto base para visualização.

    Returns:
        A **URL** para visualização do objeto no admin.
    """
    model = obj.__class__

    base_url = '/admin/{}/{}/{}/view/'.format(
        model._meta.app_label, model._meta.model_name, str(obj.pk))

    return base_url


def get_djtools_delete_object_url(obj):
    """
    Obtem a **URL** de exclusão do objeto pelo *DJTools*.

    Args:
        obj (Model): objeto base para exclusão.

    Returns:
        A **URL** para exclusão do objeto pelo *DJTools*.
    """
    model_cls = obj.__class__
    args = (model_cls._meta.app_label, model_cls._meta.model_name, obj.pk)
    return '/djtools/delete_object/%s/%s/%d/' % args


####################
# Non-Django Utils
####################


def eval_attr(obj, attr):
    """
    Obtem o valor a partir de uma string contendo atrobutos e subatributos.

    Example:
        eval_attr(<Person Túlio>, 'city.country.name') --> 'Brazil'

    Args:
        obj: objeto base para iniciar a busca;
        attr (string): string contendo os atributos na naveação.

    Returns:
        Valor de **attr** com **obj** como base.
    """
    path = attr.split('.')
    current_val = obj
    for node in path:
        if hasattr(current_val, 'get_' + node + '_display'):
            current_val = getattr(current_val, 'get_' + node + '_display')
        elif hasattr(current_val, node):
            current_val = getattr(current_val, node)
        else:
            ''
        if callable(current_val):
            current_val = current_val.__call__()
    return current_val


def randomic(size=10, allowed_chars='abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'):
    """
    Obtem um string randomica.

    Args:
        size (int): tamanho da string a gerar;
        allowed_chars (string): todos os caracteres que podem ser utilizados.

    Returns:
        String randomica com tamanho solicitado.
    Returns a randomic string.
    """
    return ''.join([choice(allowed_chars) for i in range(size)])


def dict_from_keys_n_values(keys, values):
    """
    Cria um dicionário com base em duas listas.

    Args:
        keys (list): chaves para o dicionário;
        values (list): valores para o dicionário

    Returns:
        Dict baseado nos **keys** e **values**
    """
    assert len(keys) == len(values)
    return dict(zip(keys, values))


def str_to_dateBR(value, force_4_digits_year=True):
    """
    Converte ums string no formato dia/mês/ano em um "**datetime.date**".

    Args:
        value (string): data para conversão;
        force_4_digits_year (bool): indica que o ano deve ter 4 digitos.

    Raises:
        ValueError se **value** tiver mais que 2 '/';
        ValueError se o ano não tiver 4 digitos e **force_4_digits_year** for verdadeiro.

    Returns:
        Date com base em **value**.

    """
    date_list = value.split('/')

    if len(date_list) != 3:
        raise ValueError('Data inválida.')
    if force_4_digits_year and len(date_list[2]) != 4:
        raise ValueError('O ano deve ter 4 dígitos.')

    format = (not force_4_digits_year and len(
        date_list[2]) != 4) and '%d/%m/%y' or '%d/%m/%Y'

    return datetime.strptime(value, format).date()


def str_money_to_decimal(value):
    """
    Convert uma string em um valor decimal.

    Args:
        value (string): string contendo o valor a ser convertido.

    Example:
        '1.010,10' -> Decimal('1010.00')

    Returns:
        Decimal da string passada.
    """
    value_float = float(value.replace(
        '.', '').replace(',', '.').replace(' ', ''))
    return Decimal(str(value_float))


def int_to_roman(value):
    """
    Converte um número inteiro para algarísmo romano.

    Args:
        value (int): valor a ser convertido.

    Raises:
        ValueError se não for possível converter para inteiro o valor passado;
        TypeError se o valor passado não for um *int*;
        ValueError se o valor estiver fora da faixa [0, 4000].

    Returns:
        String com o valor em algarísmo romano.
    """
    try:
        value = int(value)
    except Exception:
        raise ValueError('Expected integer, got {}'.format(type(value)))
    if not isinstance(value, int):
        raise TypeError('Expected integer, got {}'.format(type(value)))
    if not 0 < value < 4000:
        raise ValueError('Argument must be between 1 and 3999')
    ints = (1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1)
    nums = ('M', 'CM', 'D', 'CD', 'C', 'XC',
            'L', 'XL', 'X', 'IX', 'V', 'IV', 'I')
    result = []
    for i in range(len(ints)):
        count = int(value / ints[i])
        result.append(nums[i] * count)
        value -= ints[i] * count
    return ''.join(result)


def roman_to_int(input_value):
    """
    Converte um valor em algorísmo romano em inteiro.

    Args:
        input_value (string): algorísmo romano a ser convertido.

    Raises:
        TypeError se o **input_value** não for uma string;
        ValueError se não for possível a conversão.

    Returns:
        Int do algorísmo romano passado.
    """

    if not isinstance(input_value, str):
        raise TypeError("expected string, got {}".format(type(input_value)))
    input_value = input_value.upper()
    nums = {'M': 1000, 'D': 500, 'C': 100, 'L': 50, 'X': 10, 'V': 5, 'I': 1}
    sum_value = 0
    for i in range(len(input_value)):
        try:
            value = nums[input_value[i]]
            # If the next place holds a larger number, this value is negative
            if i + 1 < len(input_value) and nums[input_value[i + 1]] > value:
                sum_value -= value
            else:
                sum_value += value
        except KeyError:
            raise ValueError(
                'input is not a valid Roman numeral: {}'.format(input_value))
    # easiest test for validity...
    if int_to_roman(sum_value) == input_value:
        return sum_value
    else:
        raise ValueError(
            'input is not a valid Roman numeral: {}'.format(input_value))


def split_thousands(value, sep='.'):
    """
    Adiciona o **sep** nas centenas do valor passado.

    Args:
        value (string): valor a ser processado.

    Returns:
        String com o valor com separação de centena.

    Note:
        Se for passado um tipo numérico em **value** esse será convertido para string.
    """
    if not isinstance(value, str):
        value = str(value)
    negativo = False
    if '-' in value:
        value = value.replace('-', '')
        negativo = True
    if len(value) <= 3:
        if negativo:
            return '-' + value
        else:
            return value
    if negativo:
        return '-' + split_thousands(value[:-3], sep) + sep + value[-3:]
    else:
        return split_thousands(value[:-3], sep) + sep + value[-3:]


def mask_money(value):
    """
    Obtem o valor no formato de dinheiro.

    Args:
        value (str): Valor a ser convertido.

    Examples:
        mask_money(1) -> '1,00'
        mask_money(1000) -> '1.000,00'
        mask_money(1000.99) -> '1.000,99'

    Returns:
        String com o valor com masca.
    """
    value = str(value)
    if '.' in value:
        reais, centavos = value.split('.')
        if len(centavos) > 2:
            centavos = centavos[0:2]
    else:
        reais = value
        centavos = '00'
    reais = split_thousands(reais)
    return reais + ',' + centavos


def mask_nota(value):
    """
    Obtem a nota no formato decimal (configuração no settings).

    Args:
        value (int): Valor a ser convertido.

    Returns:
        String com o valor com máscara.
    """
    if settings.NOTA_DECIMAL:
        try:
            value = int(value)
        except Exception:
            return ''
        if settings.NOTA_DECIMAL and settings.CASA_DECIMAL == 1:
            tokens = str(value / 10).split('.')
            if len(tokens) == 1:
                value = '{},0'.format(tokens[0])
            else:
                value = '{},{}'.format(tokens[0], tokens[1][0:1])
        elif settings.NOTA_DECIMAL and settings.CASA_DECIMAL == 2:
            tokens = str(value / 100).split('.')
            if len(tokens) == 1:
                value = '{},00'.format(tokens[0])
            else:
                value = '{},{}'.format(tokens[0], tokens[1].ljust(2, '0')[0:2])
    return value


def email_valido(value):
    """
    Verifica se o valor passado é um e-mail.

    Args:
        value (string): valor a testar se é e-mail.

    Returns:
        True se o **value** for um e-mail.
    """
    try:
        validators.validate_email(value)
        return True
    except ValidationError:
        return False


def cpf_valido(value):
    """
    Verifica se o valor passado é um CPF.

    Args:
        value (string): valor a ser testado.

    Returns:
        True se o **value** for um CPF.
    """
    from djtools.forms.fields import BrCpfField

    cpf_field = BrCpfField()
    try:
        cpf_field.clean(value)
        return True
    except ValidationError:
        return False


def cnpj_valido(value):
    """
    Verifica se o valor passado é um CNPJ.

    Args:
        value (string): valor a ser testado.

    Returns:
        True se o **value** for um CNPJ.
    """
    from djtools.forms.fields import BrCnpjField

    cnpj_field = BrCnpjField()
    try:
        cnpj_field.clean(value)
        return True
    except ValidationError:
        return False


def mask_cpf(value, clean=True):
    """
    Obtem o valor passado com a mascara para CPF.

    Args:
        value (strig): valor a ser mascarado;
        clean (bool): indica se é necessário limpar o **value**.

    Examples:
        '00000000000' -> '000.000.000-00'

    Returns:
        String com mascara para CPF.
    """
    if clean:
        value = mask_numbers(value)
    if not len(value):
        return ''
    return value[:3] + '.' + value[3:6] + '.' + value[6:9] + '-' + value[9:11]


def anonimizar_cpf(value):
    """
    Anonimiza o CPF passado ocultando os 3 primeiros e os 2 ultimos digitos.

    Args:
        value (strig): valor a ser anonimizado;

    Examples:
        '00000000000' -> '***.000.000-**'

    Returns:
        CPF Anonimizado.
    """
    value = mask_numbers(value)
    if not len(value):
        return ''
    return '***' + '.' + value[3:6] + '.' + value[6:9] + '-' + '**'


def mask_cnpj(value):
    """
    Obtem o valor passado com a mascara para CNPJ.

    Args:
        value (strig): valor a ser mascarado.

    Examples:
        'XXXXXXXXXXXXXX' -> 'XX.XXX.XXX/XXXX-XX'

    Returns:
        String com mascara para CNPJ.
    """
    value = mask_numbers(value)
    return value[:2] + '.' + value[2:5] + '.' + value[5:8] + '/' + value[8:12] + '-' + value[12:14]


def mask_cep(value):
    """
    Obtem o valor passado com a mascara para CEP.

    Args:
        value (strig): valor a ser mascarado.

    Examples:
        '99999999' -> '99999-999'

    Returns:
        String com mascara para CEP.
    """
    value = mask_numbers(value)
    return value[:5] + '-' + value[5:]


def mask_numbers(value, encode=None):
    """
    Obtem os números contidos no valor passado.

    Args:
        value (string): string a ser processada;
        encode (string): codificação da string passada.

    Example:
        '012abc345def' -> '012345'

    Returns:
        String com os números contidos em **value**.
    """
    if encode:
        value = value.encode(encode)

    return re.sub(r'\D', '', str(value))


def mask_placa(value):
    """
    Obtem o valor passado com a mascara para placa de automóvel.

    Args:
        value (string): string a ser mascarado;

    Example:
        'AAA1111' -> 'AAA-1111'

    Returns:
        String com mascara para placa de automóvel.
    """
    value = str(value)
    return value[:3] + '-' + value[3:]


def datetime_to_ordinal(datetime_):
    """
    Converte um datetime para um valor orginal.

    Args:
        datetime_ (datetime): datetime a converter.

    Returns:
        Ordinal do datetime.
    """
    return mktime(datetime_.timetuple())


def ordinal_to_datetime(ordinal_):
    """
    Converte um valor orginal em um datetime.

    Args:
        ordinal_ (int): orninal a converter.

    Returns:
        Ordinal do datetime.
    """
    return datetime.fromtimestamp(ordinal_)


def date2datetime(date_):
    """
    Converte um **date** em um **datetime**.

    Args:
        date_ (date): data a ser convertida.

    Returns:
        Datetime da data passada.
    """
    return datetime(date_.year, date_.month, date_.day)


def strptime_or_default(string, format_, default=None):
    """
    Converte uma string em um datetime. Se não for possível converter o valor default é retornado.

    Args:
        string (string): string a ser convertida;
        format_ (string): formatação a ser utilizada;
        default (datetime): valor default.

    Examples:
        >>> strptime_or_default('20101011', '%Y%m%d')
        datetime.datetime(2010, 10, 11, 0, 0)
        >>> strptime_or_default('20101000', '%Y%m%d')

    Returns:
        Datetime do valor passado ou o valor default.
    """
    try:
        return datetime.strptime(string, format_)
    except Exception:
        return default


def strptime_date_or_default(string, format_, default=None):
    """
    Converte uma string em um date. Se não for possível converter o valor default é retornado.

    Args:
        string (string): string a ser convertida;
        format_ (string): formatação a ser utilizada;
        default (date): valor default.

    Examples:
        >>> strptime_or_default('20101011', '%Y%m%d')
        datetime.datetime(2010, 10, 11, 0, 0)
        >>> strptime_or_default('20101000', '%Y%m%d')

    Returns:
        Date do valor passado ou o valor default.
    """
    try:
        return datetime.strptime(string, format_).date()
    except Exception:
        return default


def get_age(begin, end=None):
    """
    Obtem o número de anos entre duas datas, caso o **end** não seja informado será utilizado a data atual.

    Args:
        begin (datetime): data inicial;
        end (datetime): data final.

    Returns:
        Inteiro com o número de anos entre **begin** e **end**.

    Note:
        Adaptado de
    """

    # adapted from http://stackoverflow.com/questions/765797/python-timedelta-in-years
    def yearsago(years, from_date=None):
        if from_date is None:
            from_date = datetime.now()
        try:
            return from_date.replace(year=from_date.year - years)
        except Exception:
            # Must be 2/29!
            assert from_date.month == 2 and from_date.day == 29  # can be removed
            return from_date.replace(month=2, day=28, year=from_date.year - years)

    if isinstance(begin, date):
        begin = date2datetime(begin)
    if end is None:
        end = datetime.now()
    else:
        if isinstance(end, date):
            end = date2datetime(end)

    num_years = int((end - begin).days / 365.25)
    if begin > yearsago(num_years, end):
        return num_years - 1
    else:
        return num_years


def format_telefone(ddd, numero):
    """
    Retorna o número de telefone formatado como (XX) XXXX-XXXX.
    O traço ficará sempre antes dos 4 últimos.
    Espaços existentes antes ou depois do ddd ou numero são removidos.

    Args:
        ddd (string): código de discagem a distância;
        numero (string): número do telefone.

    Examples:
        >>> format_telefone('84', '12345678')
        '(84) 1234-5678'
        >>> format_telefone('48', '1234567')
        '(48) 123-4567'
        >>> format_telefone('', '12345678')
        '(XX) 1234-5678'
        >>> format_telefone(' 84 ', '12345678')
        '(84) 1234-5678'
        >>> format_telefone(' 84 ', '  12345678 ')
        '(84) 1234-5678'

    Returns:
        String com o telefone mascarado.
    """
    ddd = ddd.strip()
    if not ddd:
        ddd = 'XX'

    numero = numero.strip()
    return '({}) {}-{}'.format(ddd, numero[: len(numero) - 4], numero[len(numero) - 4:])


def primeiro_dia_da_semana(data_referencia):
    """
    Obtem o primeiro dia da semana com base na data passada.

    Args:
        data_referencia (date|datetime): data de referência.

    Returns:
         Datetime com o primeiro dia da semana.
    """
    return data_referencia - timedelta(data_referencia.weekday())


###########################################################################
# ReadOnlyForm (Adaptado de http://www.djangosnippets.org/snippets/1340/) #
###########################################################################


class SpanWidget(forms.Widget):
    """
    Renderiza um valor com a tag **<span>**.

    Note:
        Deve ser utilizado no ReadonlyForm ou ReadonlyModelForm)
    """

    def render(self, name, value, attrs=None, renderer=None):
        """
        Cria o código necessário para renderizar o **value**.

        Args:
            name (string): atributo name para o span;
            value (string): valor a ser apresentado;
            attrs (dict): dicionário com um conjunto de atributos;
            renderer (): .

        Returns:
            String com **HTML** **span**.
        """
        attrs['name'] = name
        final_attrs = self.build_attrs(attrs)
        label = self.original_value
        if hasattr(self, 'label_value'):
            label = self.label_value
        return mark_safe('<span{} >{}</span>'.format(forms.utils.flatatt(final_attrs), label))

    def value_from_datadict(self, data, files, name):
        return self.original_value


class SpanField(forms.Field):
    """
    Um campo de formulário que utiliza o widget SpanWidget para apresentar o valor.
    """

    def __init__(self, label, *args, **kwargs):
        """
        Construtor.

        Args:
            label (string): rótulo para a **tag**;
            args (list): lista de argumentos;
            kwargs (dict): dicionário de argumentos nomeados.
        """
        kwargs['label'] = label
        kwargs['widget'] = kwargs.get('widget', SpanWidget)
        super().__init__(*args, **kwargs)
        self.required = kwargs.get('required', False)


def group_by(list_of_dicts, group_by_key, sub_group_by_key=None, blank_label=None, as_dict=False):
    if not list_of_dicts:
        return []
    if blank_label is None:
        blank_label = 'Nenhum'
    try:
        list_of_dicts = sorted(
            list_of_dicts, key=lambda i: str(i[group_by_key]))
    except KeyError:
        pass
    current_group = list_of_dicts[0].get(group_by_key, None) or blank_label
    grouped = [dict(group=current_group, items=[])]

    for item in list_of_dicts:
        value = item.get(group_by_key, None) or blank_label
        if value != current_group:  # create a new group
            current_group = value
            grouped.append(dict(group=current_group, items=[item]))
        else:  # an existing group
            grouped[-1]['items'].append(item)

    if sub_group_by_key:
        for g in grouped:
            g['subgroups'] = group_by(g['items'], sub_group_by_key)

    if as_dict:
        grouped_as_dict = dict()
        for g in grouped:
            subgroups_as_dict = dict()
            for s in g['subgroups']:
                subgroups_as_dict[s['group']] = s
            g['subgroups_as_dict'] = subgroups_as_dict
            grouped_as_dict[g['group']] = g
        return grouped_as_dict

    return grouped


def get_rss_links(url_file_stream_or_string):
    """
    Com base na **URL** passada, faz a leitura e retorna conteúdos *RSS*.

    Args:
        url_file_stream_or_string (string): *URL* do serviço de *RSS*.

    Returns:
        Lista contendo o conteúdo *RSS*.
    """
    import feedparser
    import urllib.parse

    feed = feedparser.parse(urllib.request.urlopen(
        url_file_stream_or_string, timeout=2))
    rss_links = []
    for entry in feed['entries'][: min(5, len(feed['entries']))]:
        entry['updated'] = entry['updated'][0:19]
        entry['updated'] = entry['updated'] + 'Z'
        title = entry['title']
        rss_links.append({'title': title, 'url': str(entry['links'][0]['href']),
                          'updated': datetime.strptime(entry['updated'], '%Y-%m-%dT%H:%M:%SZ')})
    return rss_links


def timeless_dump_qs(query):
    """
    Cria um dump de um queryset na base 64 e realiza sua assinatura.

    Args:
        query (Queryset): queryset a ser processado.

    Returns:
        String codificada na base64 do queryset.
    """
    serialized_str = base64.b64encode(
        zlib.compress(pickle.dumps(query))).decode()
    signer = Signer()
    signed_data = signer.sign(serialized_str)
    payload = {'data': signed_data}
    return mark_safe(json.dumps(payload))


def timeless_load_qs_query(query):
    """
    Com base em uma string base64 é gerado um queryset.

    Args:
        query (string): string códificada por **timeless_dump_qs**.

    Returns:
        Queryset contido na string códificada.
    """
    payload = json.loads(query)
    signer = Signer()
    signed_data = payload['data']
    data = signer.unsign(signed_data)
    return pickle.loads(zlib.decompress(base64.b64decode(data)))


def eh_nome_completo(nome):
    """
    Verifica se a string passada pode ser um nome completo.

    Args:
        nome (string): string com o nome a ser testado.

    Returns:
        True se o nome pode ser completo.
    """
    return len(nome.strip().split(' ')) > 1 and not any(i.isdigit() for i in nome)


def normalizar_nome_proprio(nome):
    """
    Normaliza o nome próprio dado, aplicando a capitalização correta de acordo com as regras e
    exceções definidas no código.

    Args:
        nome (string): string contendo o nome a ser normalizado.

    Returns:
        String com o nome normalizado.
    :return:
    """
    ponto = r'\.'
    ponto_espaco = '. '
    espaco = ' '
    regex_multiplos_espacos = r'\s+'
    regex_numero_romano = r'^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$'

    # colocando espaço após nomes abreviados
    nome = re.sub(ponto, ponto_espaco, nome or '')
    # retirando espaços múltiplos
    nome = re.sub(regex_multiplos_espacos, espaco, nome)
    nome = nome.title()  # alterando os nomes para CamelCase
    partes_nome = nome.split(espaco)  # separando as palavras numa lista
    excecoes = ['de', 'di', 'do', 'da', 'dos', 'das', 'dello', 'della', 'dalla', 'dal', 'del', 'e', 'em', 'na', 'no',
                'nas', 'nos', 'van', 'von', 'y', 'a']

    resultado = []

    for palavra in partes_nome:
        if palavra.lower() in excecoes:
            resultado.append(palavra.lower())
        elif re.match(regex_numero_romano, palavra.upper()):
            resultado.append(palavra.upper())
        else:
            resultado.append(palavra)

    nome = espaco.join(resultado)
    return nome


def get_uo_setor_listfilter(parametro_setor="setor", title_setor="setor", title_uo="campus", setor_suap=True):
    """
    Obtem filtros, para admin, de setor e unidade organizacional com base no setor passado.

    Args:
        parametro_setor (int): id do setor base para criação dos filtros;
        title_setor (string): título para o filtro de setor;
        title_uo (string): título para o filtro de unidade organizacional;
        setor_suap (bool): indica se é para utilizar a árvore de setores do SUAP.

    Returns:
        Tupla contendo as classes para filtro de setor e unidade organizacional.s
    """
    UnidadeOrganizacional = apps.get_model('rh', 'UnidadeOrganizacional')
    Setor = apps.get_model('rh', 'Setor')

    title_uo = title_uo
    parametro_uo = "%suo" % str(parametro_setor)

    qs_filter_setor = "%s__id__exact" % str(parametro_setor)
    qs_filter_uo = "%s__uo__id__exact" % str(parametro_setor)

    queryset_manager_setor = Setor.suap
    if not setor_suap:
        queryset_manager_setor = Setor.siape

    queryset_manager_uo = UnidadeOrganizacional.objects.suap()
    if not setor_suap:
        queryset_manager_uo = UnidadeOrganizacional.objects.siape()

    class SetorFilter(admin.SimpleListFilter):
        title = str(title_setor.capitalize())
        parameter_name = str(parametro_setor)

        def lookups(self, request, model_admin):
            if parametro_uo in request.GET and request.GET.get(parametro_uo):
                try:
                    return queryset_manager_setor.filter(excluido=False,
                                                         uo__id__exact=request.GET.get(parametro_uo)).values_list('id',
                                                                                                                  'sigla')
                except Exception:
                    return queryset_manager_setor.none()
            return queryset_manager_setor.filter(excluido=False).values_list('id', 'sigla')

        def queryset(self, request, queryset):
            if self.value():
                try:
                    setor = queryset_manager_setor.filter(
                        pk=request.GET.get(parametro_setor))
                    if parametro_uo in request.GET and request.GET.get(parametro_uo):
                        setor = setor.filter(uo__pk=request.GET.get(parametro_uo))
                except Exception:
                    setor = queryset_manager_setor.none()
                if setor.exists():
                    return queryset.filter(**{qs_filter_setor: self.value()})
                else:
                    self.used_parameters.pop(self.parameter_name)
            return queryset

    class UoFilter(admin.SimpleListFilter):
        title = str(title_uo.capitalize())
        parameter_name = str(parametro_uo)

        def lookups(self, request, model_admin):
            return queryset_manager_uo.all().values_list('id', 'sigla')

        def queryset(self, request, queryset):
            if self.value():
                try:
                    uo = queryset_manager_uo.filter(
                        pk=request.GET.get(parametro_uo))
                except Exception:
                    uo = queryset_manager_uo.none()
                if uo.exists():
                    return queryset.filter(**{qs_filter_uo: self.value()})
                else:
                    self.used_parameters.pop(self.parameter_name)
            return queryset

    return (UoFilter, SetorFilter)


class SuapProcessThread(threading.Thread):
    """
    Classe para processamento de threads especialidas no SUAP.
    """

    def __init__(self, callback=None, *args, **kwargs):
        """
        Construtor.

        Args:
            callback (Callable): função a ser invocada em um callback;
            args (list): lista com argumentos posicionais;
            kwargs (dict): dicionário com argumentos nomeados.
        """
        self._callback = callback
        self._target = kwargs['target']
        super().__init__(*args, **kwargs)

    def run(self):
        """
        Método de execução por parte do Thread.
        """
        if settings.DEBUG:
            self._target()
        else:
            try:
                if self._target:
                    self._target()
            except BaseException as e:
                if self._callback is None:
                    raise e
                else:
                    self._callback(self, e)


@deprecated('por favor utilizar Tasks')  # NOQA
class SuapProcess:
    """
    Classe utilizada para processamento em segundo plano de atividades iniciadas pelos clientes (web browsers).
    """
    #: Arquivo do tipo XLS - Planilha eletrônica
    ARQUIVO_XLS = 1
    #: Arquivo do tipo ZIP
    ARQUIVO_ZIP = 2
    #: Arquivo do tipo PDF
    ARQUIVO_PDF = 3
    #: Arquivo do tipo CSV - Arquivo separado por vírgula
    ARQUIVO_CSV = 4
    #: Arquivo do tipo TXT - Texto
    ARQUIVO_TXT = 5

    def __init__(self, description, total, request, download=0):
        """
        Construtor.

        Args:
            description (string): descrição do processo;
            total (int): total de registros a processar;
            request (HttpRequest): objeto request;
            download ():
        """
        self.pid = str(uuid.uuid4())
        description = description
        self.user = request.user
        self.request = request
        self.process = dict(pid=self.pid, description=description, total=total, percentual=1, message=None, error=False,
                            url=None, download=download, user=self.user.username)
        cache.set(self.pid, self.process, 86400)
        self.url = '/djtools/process/%s/' % self.pid
        self.partial = 0

    def update(self, parcial):
        """
        Método que atualiza o número de itens processados para cálculo do percentual.

        Args:
            parcial (int): número de itens processados.
        """
        if not self.process['message']:
            self.process = cache.get(self.pid)
            self.process['percentual'] = int(
                parcial * 100 / (self.process['total'] or 1)) or 1
            cache.set(self.process['pid'], self.process, 86400)

    def proximo(self, count=1, interval=100):
        """
        Indica que outro item foi processado.

        Args:
            count (int):
            interval (int):
        """
        self.partial += count
        if self.partial < 100 or self.partial % interval == 0:
            self.update(self.partial)

    def __next__(self):
        """
        Sobrecarga do método para uso em interators.

        Returns:
            Próximo item do conjunto.
        """
        return self.proximo()

    def iterate(self, iterable):
        """
        Realiza a iteração em um conjunto de dados. Estilo gerador.

        Args:
            iterable (iterable): conjunto com dados a iterar.

        Returns:
            Objeto do conjunto.
        """
        yield from iterable

    def finalize(self, message, url, error=False, file_path=None):
        """
        Realiza os últimos procedimentos ao término da thread, independente de sucesso ou não.

        Args:
            message:
            url:
            error:
            file_path:
        """
        self.process['percentual'] = 100
        self.process['message'] = message
        self.process['error'] = error
        self.process['file_path'] = file_path
        self.process['url'] = url
        cache.set(self.process['pid'], self.process, 86400)
        if 'send_email' in self.process:
            titulo = '[SUAP] Resultado da Execução do Processo %s' % self.pid
            mensagem = '<h1>Resultado da Execução do Processo %s</h1>' '<p>O resultado está disponível no endereço: %s/djtools/process/%s.</p>' % (
                self.pid,
                settings.SITE_URL,
                self.pid,
            )
            send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.user.get_vinculo()],
                              categoria='Resultado da Execução do Processo')

    def HttpResponse(self, interval=5000):
        return httprr('/djtools/process/{}/{}/'.format(self.pid, interval))

    def erro(self, exception, mensagem):
        if settings.DEBUG:
            print((exception, mensagem))
        capture_exception(exception)
        self.finalize('Erro ao executar a atividade.',
                      self.request.META.get('HTTP_REFERER', '..'), True)

    def start(self, do, force_threading=False):
        from djtools.testutils import running_tests

        if not force_threading and (running_tests() or self.process['total'] < 100):
            do()
        else:
            thread = SuapProcessThread(target=do, callback=self.erro)
            thread.start()


def montar_timeline_horizontal(queryset, data_inicio_referencia, data_fim_referencia, qs_data_inicio, qs_data_fim,
                               descricao_celula, title="Timeline"):
    """
    Cria o código **HTML** para uma timeline horizontal.

    Args:
        queryset (Queryset): queryset com resultado para gerar a timeline;
        data_inicio_referencia (datetime): data inicial de referência;
        data_fim_referencia (datetime): data final de referência;
        qs_data_inicio (string): nome do atributo da data inicial para comparação;
        qs_data_fim (string): nome do atributo da data final para comparação;
        descricao_celula (string): nome do atributo que representa o objeto.
        title (string): texto com o título da timeline.

    Returns:
        String contendo o código da timeline.
    """
    if not queryset:
        return ''
    html = (
        '''
        <table class="timeline-horizontal">
            <thead>
            <tr>
                <th>%s</th>
        '''
        % title
    )
    tamanho_qs = Decimal(
        (data_fim_referencia - data_inicio_referencia + timedelta(1)).days)
    queryset = queryset.order_by(qs_data_inicio)
    celulas = OrderedDict()
    for idx, objeto in enumerate(queryset):
        if celulas.get(objeto.__getattribute__(descricao_celula)):
            celulas.get(objeto.__getattribute__(descricao_celula)).append(idx)
        else:
            celulas[objeto.__getattribute__(descricao_celula)] = [idx]

        data_inicio = objeto.__getattribute__(qs_data_inicio)
        data_fim = objeto.__getattribute__(qs_data_fim)
        if not data_fim or data_fim > data_fim_referencia:
            data_fim = data_fim_referencia

        if data_inicio < data_inicio_referencia:
            data_inicio = data_inicio_referencia

        width = Decimal((data_fim - data_inicio + timedelta(1)
                         ).days) * Decimal(90) / tamanho_qs
        html += '''
            <th style="width:{}%">
                <span> {}/{}
                    <strong>{}</strong>
                </span>
        '''.format(
            width,
            data_inicio.day,
            data_inicio.month,
            data_inicio.year,
        )
        if idx + 1 == len(queryset):
            html += '''
                <span class="final">{}/{}
                    <strong>{}</strong>
                </span>
            '''.format(
                data_fim.day,
                data_fim.month,
                data_fim.year,
            )

        html += '</th>'

    html += '''
        </tr>
    </thead>
    <tbody>
    '''
    for chave, colunas in list(celulas.items()):
        html += (
            '''
            <tr>
                <td>%s</td>'''
            % chave
        )
        for index in range(0, queryset.count()):
            if index in colunas:
                html += '<td class="default"></td>'
            else:
                html += '<td></td>'
        html += '</tr>'
    html += '</tbody></table>'
    return html


def tooltip_text(text, description):
    """
    Cria um **span** para ser utilizado como tooltip.

    Args:
        text (string): texto apresentado ao cliente;
        description (string): texto apresentado ao passar o mouse no texto.

    Returns:
        String contendo o código do **span**
    """
    return '<span class="hint" data-hint="{}">{}</span>'.format(description, text)


def class_herdar(cls_base, cls_super):
    """
    Adiciona herança a uma classe.

    Args:
        cls_base: classe base;
        cls_super: classe superior.
    """
    bases = list(cls_base.__bases__)
    bases.insert(0, cls_super)
    cls_base.__bases__ = tuple(OrderedDict.fromkeys(bases))


def sub_instances(instance):
    """
    Obtem todas as sub instâncias de um objeto de modelo.

    Args:
        instance (Model): instância a processar.

    Returns:
        Lista com as instãncias das sub instâncias.
    """

    def inner(instance, children=[]):
        children.append(instance)
        fields = [f for f in instance._meta.get_fields() if (
            f.one_to_many or f.one_to_one) and f.auto_created]
        for field in fields:
            try:
                if issubclass(field.related_model, instance._meta.model) or issubclass(instance._meta.model,
                                                                                       field.related_model):
                    obj = getattr(instance, field.name)
                    if obj not in children:
                        inner(obj, children)
            except Exception:
                pass
        return list(set(children))

    return inner(instance, [])


def related_objects(obj):
    """
    Obtem os objetos relacionados a um objeto de modelo.

    Args:
        obj (Model): objeto de modelo.

    Returns:
        Objeto de modelo relacionado com **obj**.
    """
    collector = NestedObjects(using=router.db_for_write(obj))
    collector.collect([obj])

    def flatten(elem):
        if isinstance(elem, list):
            return chain.from_iterable(list(map(flatten, elem)))
        elif obj != elem:
            return (elem,)
        return ()

    result = flatten(collector.nested())
    return result


def can_hard_delete(obj):
    """
    Verifica se é possível apagar um objeto de modelo.

    Args:
        obj (Model): objeto de modelo.

    Returns:
         True se for possível apagar o objeto de modelo.
    """
    for item in related_objects(obj):
        if not item in sub_instances(obj):
            return False
    return True


def can_hard_delete_fast(obj):
    """
    Verifica se é possível apagar um objeto de forma segura. Para tal, é verificado se existe alguma relação com o objeto.

    Args:
        obj (Model): objeto de modelo.

    Returns:
         True se for possível apagar o objeto de modelo.
    """
    heirs = sub_instances(obj)
    for heir in heirs:
        fields = [f for f in heir._meta.get_fields() if (f.one_to_many) and f.auto_created] + [f for f in
                                                                                               heir._meta.get_fields(
                                                                                                   include_hidden=True)
                                                                                               if f.many_to_many]
        for field in fields:
            rel_obj = hasattr(field, 'get_accessor_name') and getattr(heir, field.get_accessor_name()) or getattr(heir,
                                                                                                                  field.name)
            if rel_obj.exists():
                return False
    return True


def imprimir_percentual(queryset, desabilitar_percentual=False):
    """
    Imprimi percentual de execução em modo terminal.

    Args:
        queryset (Queryset): queryset a processar;
        desabilitar_percentual (bool): indica se é para apresentar o progresso.

    Returns:
        Item do queryset.
    """
    if not desabilitar_percentual:
        count = 0
        total = queryset.count()
        for item in queryset:
            count += 1
            porcentagem = int(float(count) / total * 100)
            sys.stdout.write(termcolors.make_style(fg='cyan', opts=('bold',))(
                '\r[{}] {}% - Atualizando {} de {}'.format('#' * (porcentagem // 10), porcentagem, count, total)))
            sys.stdout.flush()
            yield item
    else:
        for item in queryset:
            yield item


def years_between(start, end):
    """
    Cálcula o número de anos entre duas datas.

    Args:
        start (datetime): data inicial;
        end (datetime): data final.

    Returns:
        Número de anos.
    """
    if not isinstance(start, datetime):
        start = datetime(start.year, start.month, start.day)
    if not isinstance(end, datetime):
        end = datetime(end.year, end.month, end.day)
    return end.year - start.year - ((end.month, end.day) < (start.month, start.day))


def get_real_sql(queryset, remove_order_by=False):
    """
    Obtem a consulta (**SQL**) a partir de um queryset.

    Args:
        queryset (Queryset): queryset com os filtros;
        remove_order_by (bool): indica que deve-se retirar a cláusula order by do queryset.

    Returns:
        String com a pesquisa (**SQL**) realizada pelo queryset.
    """
    if remove_order_by:
        queryset.query.clear_ordering(force_empty=True)
    sql, params = queryset.query.sql_with_params()
    cursor = connection.cursor()
    cursor.execute(sql, params)
    return str(cursor.db.ops.last_executed_query(cursor, sql, params))


def save_session_cache(request, key, func):
    """
    Salva os dados em sessão.

    Args:
        request (HttpRequest): objeto requeste;
        key (string): chave utilizada para indexar o resultado no cache;
        func (Function): função a ser invocada caso não esteja em cache seu resultado;

    :return:
    """
    if running_tests():
        return func()
    value = func()
    session_key = '_cache_{}'.format(key)
    try:
        request.session[session_key] = [datetime.now(), pickle.dumps(value)]
        request.session.save()
    except Exception:
        pass
    return value


def get_session_cache(request, key, func, timeout):
    """
    Obtem o resultado de uma função com base no cache, caso não tenha esteja em cache, o resultado é colocado em cache.

    Args:
        key (string): chave utilizada para indexar o resultado no cache;
        func (Function): função a ser invocada caso não esteja em cache seu resultado;
        timeoout (int): tempo máximo de vida para o cache.

    Returns:
        Resultado da função passada.
    """
    if running_tests() or settings.DEBUG:
        return func()
    now = datetime.now()
    session_key = '_cache_{}'.format(key)
    if session_key in request.session and request.session[session_key][0] + timedelta(seconds=timeout) > now:
        return pickle.loads(request.session[session_key][1])
    else:
        return save_session_cache(request, key, func)


def get_cache(key, func, timeout):
    """
    Obtem o resultado de uma função com base no cache, caso não tenha esteja em cache, o resultado é colocado em cache.

    Args:
        key (string): chave utilizada para indexar o resultado no cache;
        func (Function): função a ser invocada caso não esteja em cache seu resultado;
        timeoout (int): tempo máximo de vida para o cache.

    Returns:
        Resultado da função passada.
    """
    if running_tests() or settings.DEBUG:
        return func()
    key = '_cache_' + key
    data = cache.get(key)
    if data:
        retorno = pickle.loads(data)
        return retorno
    else:
        retorno = func()
        cache.set(key, pickle.dumps(retorno), timeout)
        return retorno


def walk(path):
    """
    Função que navega a partir de uma raiz nos diretórios do sistema opracional.

    Args:
        path (string): contem o diretório base para navegação.

    Returns:
        Lista contendo a raiz, os diretórios e os arquivos.
    """
    for root, dirs, files in os.walk(path, topdown=True):
        dirs[:] = [d for d in dirs if d in settings.INSTALLED_APPS_SUAP]
        yield [root, dirs, files]


def b64encode(content):
    """
    Método que converte um conteúdo original para um conteúdo base 64.

    Args:
        content: string ou byte

    Raises:
        Exception caso o **content_64** não seja um string ou bytes.

    Returns:
        String na base b4 caso o parâmetro de entrada seja uma string e byte na base 64 caso o parâmetro de
        entrada seja bytes.
    """
    if isinstance(content, str):
        return base64.b64encode(content.encode()).decode()
    elif isinstance(content, bytes):
        return base64.b64encode(content)
    else:
        raise Exception(
            'O método b64encode só aceita como parâmetro de entrada uma String ou Bytes.')


def b64decode(content_b64):
    """
    Método que converte um conteúdo base 64 para o conteúdo original.

    Args:
        content_b64 (string): string base 64 ou bytes na base 64

    Raises:
        Exception caso o **content_64** não seja um string ou bytes.

    Returns:
        String "original" caso o parâmetro de entrada seja uma string base 64 e byte "original" caso caso o parâmetro
        de entrada seja bytes base 64.
    """
    if isinstance(content_b64, str):
        return base64.b64decode(content_b64.encode()).decode()
    elif isinstance(content_b64, bytes):
        return base64.b64decode(content_b64)
    else:
        raise Exception(
            'O método b64decode só aceita como parâmetro de entrada String ou Bytes.')


def rgetattr(obj, attr, *args):
    """
    Obtem um atributo pertence a um objeto de forma recursiva.

    Args:
        obj (object): objeto base para pesquisa;
        attr (string): atributo a ser pesquisado, formato: atributo.atributo.atributo ...;
        args: (): argumentos extras

    Returns:
        Atributo seguindo a pesquisa por attr em obj.
    """

    def _getattr(obj, attr):
        return getattr(obj, attr, *args)

    return functools.reduce(_getattr, [obj] + attr.split('.'))


def rhasattr(obj, attr, *args):
    """
    Verifica se um atributo pertence a um objeto de forma recursiva.

    Args:
        obj (object): objeto base para pesquisa;
        attr (string): atributo a ser pesquisado, formato: atributo.atributo.atributo ...;
        args: (): argumentos extras

    Returns:
        True se existir o atributo.
    """

    def _hasattr(obj, attr):
        return hasattr(obj, attr, *args)

    return functools.reduce(_hasattr, [obj] + attr.split('.'))


def get_module_from_url(url):
    """
    Retorna o nome completo de um módulo a partir de uma URL

    Args:
         url (string): URL completa do suap, exemplo: https://suap.ifrn.edu.br/admin/erros/erro/add/

    Returns:
        String se o módulo existir e a URL for bem formada, senão retorna None.
    """

    try:
        path = urlparse(url).path
        resolve(path)
        path = path.split('/')
        if len(path) < 3:
            return 'djtools'
        modulo = path[1] != 'admin' and path[1] or path[2]
        apps.get_app_config(modulo)
        return modulo
    except Exception:
        return None


def get_view_name_from_url(url):
    """
    Retorna o namespace de uma view a partir de uma URL

    Args:
         url (string): URL completa do suap, exemplo: https://suap.ifrn.edu.br/admin/erros/erro/add/

    Returns:
        String se o módulo existir e a URL for bem formada, senão retorna None.
    """
    try:
        path = urlparse(url).path
        if path.startswith('/admin'):
            splitted_path = path.split('/')
            url_name = resolve(path).url_name or splitted_path[3]
            return '{}.{}.{}'.format(splitted_path[1], splitted_path[2], url_name)
        else:
            view_func = resolve(path)[0]
            return view_func.__module__ + '.' + view_func.__name__
    except Exception:
        return None
