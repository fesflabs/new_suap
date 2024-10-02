import base64
import math
import re
import os
from datetime import timedelta, datetime, date
from decimal import Decimal

from django.utils.html import escape
from django.utils.safestring import SafeText
from dateutil.relativedelta import relativedelta
from django import template
from django.apps import apps
from django.db.models import QuerySet
from django.template.defaultfilters import pluralize
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from django.conf import settings

from comum.utils import formata_segundos, data_extenso, extenso, tl
from djtools.choices import campos, Meses
from djtools.utils import mask_money, mask_nota, mask_numbers, anonimizar_cpf as anonimizador_cpf
from djtools.utils import split_thousands, to_ascii, normalizar_nome_proprio

register = template.Library()


@register.filter
def formatar_extenso(data):
    """
    Filtro que escreve datas por extenso.

    Args:
        data (date/datetime): data a ser escrita por extenso.

    Returns:
        String com a data escrita por extenso.
    """
    return data_extenso(data)


@register.filter(name='length')
def length(value):
    """
    Filtro que retorna o tamanho do conjunto passado.

    Args:
        value (): elemento a ser contado.

    Returns:
        Int com o tamanho de **value**.

    Note:
        O value pode ser um list, um dict ou um Queryset.
    """
    if issubclass(type(value), QuerySet):
        return value.count()
    try:
        return len(value)
    except (ValueError, TypeError):
        return 0


@register.filter
def getval(form, key):
    """
    Obtem o valor para uma chave em um dicionário.

    Args:
        form (dict): dicionário;
        key (string): chave de pesquisa do elemento.

    Returns:
         Valor contido em **key** no dicionário passado.
    """
    return form[key]


@register.filter
def getval_label(form, key):
    """
    Obtem o **label** de um field em um formuário.

    Args:
        form (Forms): formulário;
        key (string): nome do campo.

    Returns:
         String com o **label** do campo.
    """
    return form[key].label


@register.filter
def set_periodo_letivo_referencia(obj, periodo_letivo):
    """
    Atribui o **periodo_letivo** para o **obj**.

    Args:
        obj (Model): objeto de modelo;
        periodo_letivo (): período letivo.

    Returns:
        String vazia.
    """
    if periodo_letivo and int(periodo_letivo):
        obj.periodo_letivo_referencia = periodo_letivo
    return ''


@register.filter
def set_ano_letivo_referencia(obj, ano_letivo):
    """
    Atribui o **ano_letivo** para o **obj**.

    Args:
        obj (Model): objeto de modelo;
        periodo_letivo (): ano letivo.

    Returns:
        String vazia.
    """
    if ano_letivo:
        obj.ano_letivo_referencia = ano_letivo
    return ''


@register.filter
def validjs_symbol(str):
    """
    Retira caracteres que são problemáricos no javascript.

    Args:
        str (string): texto a ser processado.

    Returns:
        String com **str** sem caracters.
    """
    return str.replace("-", "")


@register.filter
def format_timedelta(delta):
    """
    Formata um **timedelta**.

    Args:
        delta: delta a ser formatada.

    Returns:
        String formatada.

    Notes:
        Filtro utilizado em **format_**.
    """
    return timesince(datetime(1980, 1, 1), datetime(1980, 1, 1) + delta)


@register.filter(is_safe=True)
def format_bool(value, html=True):
    """
    Formata um **bool**.

    Args:
        value (bool): boolean a formatar;
        html (bool): indica se o formato de saída deve ser **HTML**.

    Returns:
        String contendo 'Sim' ou 'Não' de acordo com o bool.

    Notes:
        Filtro utilizado em **format_**.
    """
    if html:
        retorno = '<span class="status status-{}">{}</span>'.format(value and 'success' or 'error', value and 'Sim' or 'Não')
        return format_html(retorno)
    return '{}'.format(value and 'Sim' or 'Não')


@register.filter(is_safe=True)
def format_datetime(value):
    """
    Formata um **datetime**.

    Args:
        value: datetime a ser formatada.

    Returns:
        String formatada.

    Notes:
        Filtro utilizado em **format_**.
    """
    try:
        if hasattr(value, 'time'):
            return value.strftime('%d/%m/%Y %H:%M:%S')
        else:
            return value.strftime('%d/%m/%Y')
    except ValueError:
        return value
    except Exception:
        return '-'


@register.filter(is_safe=True)
def format_money(value):
    """
    Formata um **money**.

    Args:
        value: valor a ser formatada.

    Examples:
        format_money(1) -> '1,00'
        format_money(1000) -> '1.000,00'
        format_money(1000.99) -> '1.000,99'

    Returns:
        String formatada.

    Notes:
        Filtro utilizado em **format_**.
    """
    if value not in [None, '']:
        value = str(value)
        if '.' in value:
            reais, centavos = value.split('.')
            if len(centavos) > 2:
                centavos = centavos[0:2]
        else:
            reais = value
            centavos = '00'
        reais = split_thousands(reais)
        return str(reais + ',' + centavos)
    return '-'


@register.filter(is_safe=True)
def format_money_with_sign(value):
    """
    Formata um **money**.

    Args:
        value: valor a ser formatada.

    Returns:
        String formatada.

    Notes:
        Filtro utilizado em **format_**.
    """
    if value not in [None, '']:
        return "R$ {}".format(format_money(value))
    return '-'


@register.filter(name='format_iterable')
def format_iterable(value, middle_separator=', ', final_separator=_('and')):
    """
    Formata um iterável.

    Args:
        value: valor a ser formatada;
        middle_separator (string): separador de itens;
        final_separator (string): separador para o último item.

    Examples:
        format_iterable([1]) -> '1'
        format_iterable([1, 2]) -> '1 e 2'
        format_iterable([1, 2, 3]) -> '1, 2 e 3'

    Returns:
        String formatada.

    Notes:
        Filtro utilizado em **format_**.
    """
    values = []
    for i in value:
        if isinstance(i, bytes):
            values.append(i.decode())
        else:
            values.append(str(format_(i)))
    if len(value) == 0:
        return '-'
    if len(value) == 1:
        return values[0]
    else:
        return '{} {} {}'.format(middle_separator.join(values[:-1]), final_separator, values[-1])


@register.filter(name='format_daterange')
def format_daterange(value1, value2):
    """
    Formata um intervalo de datas.

    Args:
        value1 (datetime): data inicial do intervalo;
        value2 (datetime): data final do intervalo;

    Returns:
        String formatada.

    Notes:
        Filtro utilizado em **format_**.
    """
    return '{} a {}'.format(format_datetime(value1), format_datetime(value2))


@register.filter
def format_user(obj, nome=None):
    """
    Formata um objeto **user**.

    Args:
        obj (User): objeto *User*;
        nome (string): nome do usuário.

    Returns:
        String formatada.

    Notes:
        Filtro utilizado em **format_**.
    """
    # obj: id da pessoa física
    User = apps.get_model('comum', 'User')
    PrestadorServico = apps.get_model('comum', 'PrestadorServico')
    Servidor = apps.get_model('rh', 'Servidor')

    list_vinculos = [Servidor, PrestadorServico]
    if 'edu' in settings.INSTALLED_APPS:
        Aluno = apps.get_model('edu', 'Aluno')
        list_vinculos.append(Aluno)

    user = None
    nome = ''
    if isinstance(obj, str):
        profile_id = obj
    else:
        if type(obj) == User:
            user = obj
        elif type(obj) in list_vinculos:
            user = obj.get_user()
        if user:
            profile_id = user.uuid
            if hasattr(user, 'get_profile') and user.get_profile():
                nome = user.get_profile().nome_usual or user.get_profile().nome
            else:
                return user.get_full_name()
        else:
            profile_id = hasattr(obj, 'uuid') and obj.uuid or obj.pessoa_fisica.uuid
            nome = obj.username

    absolute_url = '#'
    nome = nome or '-'
    if user:
        absolute_url = user.get_relacionamento() and user.get_relacionamento().get_absolute_url()
    return mark_safe(
        '''<div class="popup-user">
                <a href="{url}" class="popup-user-trigger" data-user-id="{id}">{nome}</a>
            </div>'''.format(
            nome=normalizar_nome_proprio(nome), id=profile_id, url=absolute_url
        )
    )


@register.filter
def format_image(value):
    return mark_safe('<div class="photo-circle"><img src={}/></div>'.format(value))


@register.filter
def index(indexable, i):
    return indexable[int(i)]


@register.filter
def classname(obj):
    return obj.__class__._meta.verbose_name


@register.filter
def format_profile(obj, nome=None):
    """
    Formata um objeto **Profile**.

    Args:
        obj (Profile): objeto *Profile*;
        nome (string): nome do usuário.

    Returns:
        String formatada.

    Notes:
        Filtro utilizado em **format_**.
    """
    # obj: id da pessoa física
    Pessoa = apps.get_model('rh', 'Pessoa')
    Funcionario = apps.get_model('rh', 'Funcionario')
    PessoaFisica = apps.get_model('rh', 'PessoaFisica')
    PessoaJuridica = apps.get_model('rh', 'PessoaJuridica')

    profile = None
    if isinstance(obj, str):
        profile_id = obj

    else:
        if type(obj) in [Pessoa, Funcionario]:
            if hasattr(obj, 'pessoafisica'):
                profile = obj.pessoafisica
            elif hasattr(obj, 'pessoa_fisica'):
                profile = obj.pessoa_fisica
            elif hasattr(obj, 'pessoajuridica'):
                profile = obj.pessoajuridica
        elif type(obj) == PessoaFisica:
            profile = obj
        elif type(obj) == PessoaJuridica:
            profile = obj
        if profile:
            if hasattr(profile, 'pessoa'):
                profile_id = profile.pessoa.uuid
            else:
                profile_id = profile.uuid
            nome = profile.nome_usual or profile.nome
            if type(profile) == PessoaJuridica:
                nome = str(profile)
        else:
            profile_id = obj.uuid
            nome = obj.username
    user = tl.get_user()
    if user and user.is_anonymous:
        return normalizar_nome_proprio(nome)
    nome = nome or '-'
    return mark_safe(
        '''<div class="popup-profile">
                <a href="#" class="popup-profile-trigger" data-profile-id="{id}">{nome}</a>
            </div>'''.format(
            nome=normalizar_nome_proprio(nome), id=profile_id
        )
    )


@register.filter(is_safe=True)
def format_phone(value):
    """
    Formata uma string no formato de telefone.

    Args:
        value (string): número a ser formatado.

    Returns:
        String formatada.

    Notes:
        Filtro utilizado em **format_**.
    """
    try:
        non_decimal = re.compile(r'[^\d.]+')
        numero = non_decimal.sub('', value)
        if len(numero) == 11:
            return '({}) {}-{}'.format(numero[0:2], numero[2:7], numero[7:11])
        elif len(numero) == 10:
            return '({}) {}-{}'.format(numero[0:2], numero[2:6], numero[6:10])
        else:
            return value
    except ValueError:
        return value


@register.filter(is_safe=True)
def format_permission(value):
    """
    Formata/Traduz um valor para uma string de permission.

    Args:
        value (string): string da permission.

    Returns:
        String formatada.

    Notes:
        Filtro utilizado em **format_**.
    """
    if "Can add" in value:
        return "Pode adicionar%s" % value.split("Can add")[1]
    elif "Can change" in value:
        return "Pode gerenciar%s" % value.split("Can change")[1]
    elif "Can delete" in value:
        return "Pode remover%s" % value.split("Can delete")[1]
    elif "Can view" in value:
        return "Pode visualizar%s" % value.split("Can view")[1]
    return value


@register.filter(name='nbsp')
def nbsp(value):
    """
    Substitui espaços em branco, em um string, pelo código **HTML**.

    Args:
        value (string): texto a processar.

    Returns:
        String com os espaços em branco substituídos por *&nbsp;*.
    """
    return mark_safe(str(value or '').replace(' ', '&nbsp&nbsp&nbsp&nbsp'))


@register.filter(name='remove_nbsp')
def remove_nbsp(value):
    """
    Remove espaços em branco ocultos no html.

    Args:
        value (string): texto a processar.

    Returns:
        String com os espaços html em branco oculto removidos.
    """
    value = str(value or '')
    regex = "<span(.*?)>&nbsp;</span>"
    result = re.search(regex, value)
    if result:
        for span in result.groups():
            value = value.replace('<span{}>&nbsp;</span>'.format(span), '')
    return mark_safe(value)


@register.filter(name='format', is_safe=True)
def format_(value, html=True):
    """
    Formata o valor passado, deixando em um formato amigável.

    Args:
        value: valor a ser formatado;
        html (bool): indica se a saída deve ser **HTML**.

    Returns:
        String com o valor passado formatado.
    """
    if value in (None, ''):
        return '-'
    elif isinstance(value, bytes):
        return value.decode()
    elif isinstance(value, bool):
        return format_bool(value, html)
    elif isinstance(value, timedelta):
        return format_timedelta(value)
    elif value.__class__.__name__ == 'Decimal' or isinstance(value, float):
        return format_money(value)
    elif hasattr(value, 'strftime'):
        return format_datetime(value)
    elif hasattr(value, '_meta') and value._meta.model_name in ('user', 'servidor', 'prestadorservico', 'aluno'):
        if html:
            return format_user(value)
        else:
            return str(value)
    elif hasattr(value, '_meta') and value._meta.model_name in ('pessoa', 'pessoafisica', 'funcionario', 'pessoajuridica'):
        if html:
            return format_profile(value)
        else:
            return str(value)
    elif isinstance(value, str):
        return value
    elif hasattr(value, '__iter__'):
        return format_iterable(value)
    elif hasattr(value, 'all'):
        return format_iterable(value.all())
    else:
        return value


@register.filter(name='format_br', is_safe=True)
def format_br(value):
    """
    Formata uma string substituindo quebras de linha pela tag **<br>**.

    Args:
        value (string): string a formatar.

    Returns:
        String com o valor passado formatado.
    """
    if value:
        value = value.replace('\n', '<br>')
    return format_(value)


@register.filter(name='format_time', is_safe=True)
def format_time(value):
    """
    Formata um datetime no formato hh:mm:ss.

    Args:
        value (datetime): objeto datetime a ser formatado.

    Returns:
        String com o valor passado formatado.
    """
    return '{}'.format(formata_segundos(value, '{h:02.0f}:', '{m:02.0f}:', '{s:02.0f}'))


@register.filter(name='format_time_hms', is_safe=True)
def format_time_hms(value):
    """
    Formata um datetime no formato hh:mm:ss.

    Args:
        value (datetime): objeto datetime a ser formatado.

    Returns:
        String com o valor passado formatado.
    """
    return '{}'.format(formata_segundos(value, '{h}h ', '{m}min ', '{s}seg '))


@register.filter
def sum_values_by_key(list_of_dicts, key):
    """
    Realiza o somatório de em uma chave de dicionário em uma lista de dicionários.

    Args:
        list_of_dicts (list): lista contendo os dicionários;
        key (string): chave a ser somada.

    Returns:
         Soma do valor solicitado.
    """
    if hasattr(list_of_dicts, 'values'):
        list_of_dicts = list(list_of_dicts.values())
    return sum(d.get(key, 0) for d in list_of_dicts)


@register.filter
def sum_all_dict_values(dictionary):
    """
    Soma todos os valores de um dicionário ou de um dicionário de dicionários.

    Args:
        dictionary: dicionário ou dicionário de dicionários.

    Returns:
        Soma de todos os valores.
    """
    sum_ = 0
    if isinstance(dictionary, dict):
        for k, v in list(dictionary.items()):
            if isinstance(v, dict):
                sum_ += sum_all_dict_values(v)
            else:
                try:
                    sum_ += Decimal(str(v))
                except Exception:
                    sum_ += 0
    return sum_


@register.filter(name='get_ldap_attr')
def get_ldap_attr(dic, key):
    # TODO: mover para a app ldap_backend

    from ldap_backend.utils import ad_to_datetime

    val = dic.get(key, [''])

    if isinstance(val, str):
        return val

    elif len(val) == 1:
        val = val[0]
        try:
            if type(val) != str:
                val = val.decode('utf-8')
        except Exception:
            if key == 'thumbnailPhoto':
                val = base64.b64encode(val).decode('utf-8')
            else:
                val = '??????????'
        if key == 'thumbnailPhoto':
            return mark_safe(f'<img src="data:image/jpeg;base64,{val}"/>')
        if key in ['accountExpires', 'pwdLastSet', 'badPasswordTime', 'lastLogonTimestamp']:
            if not val or val in ['0', '9223372036854775807']:
                return 'Nunca'
            else:
                return ad_to_datetime(val)
        if key == 'userAccountControl':
            map_ = {
                '512': 'Enabled Account',
                '514': 'Disabled Account',
                '544': 'Enabled, Password Not Required',
                '546': 'Disabled, Password Not Required',
                '66048': 'Enabled, Password Doesn\'t Expire',
                '66050': 'Disabled, Password Doesn\'t Expire',
                '66080': 'Enabled, Password Doesn\'t Expire & Not Required',
                '66082': 'Disabled, Password Doesn\'t Expire & Not Required',
                '262656': 'Enabled, Smartcard Required',
                '262658': 'Disabled, Smartcard Required',
                '262688': 'Enabled, Smartcard Required, Password Not Required',
                '262690': 'Disabled, Smartcard Required, Password Not Required',
                '328192': 'Enabled, Smartcard Required, Password Doesn\'t Expire',
                '328194': 'Disabled, Smartcard Required, Password Doesn\'t Expire',
                '328224': 'Enabled, Smartcard Required, Password Doesn\'t Expire & Not Required',
                '328226': 'Disabled, Smartcard Required, Password Doesn\'t Expire & Not Required',
            }
            return '{} ({})'.format(val, map_.get(val, '?'))
        return val

    else:  # Múltiplos valores para o atributo
        out = ['<ul>']
        for v in val:
            out.append('<li>%s</li>' % v.decode('utf-8'))
        out.append('</ul>')
        return mark_safe(''.join(out))


@register.filter
def percentage(quantity, total):
    """
    Calcula o valor percentual entre a quantidade passada e o total.

    Args:
        quantity (): quantidade a calcular;
        total (): total dos itens.

    Returns:
        Float com o valor percentual entre **quantity** e **total**.
    """
    try:
        return float(quantity) / total * 100
    except Exception:
        return 0


@register.filter
def count_entries_in_dictlist(dictlist, args):
    """
    Calcula o número de itens em uma lista de dicionários. Os items a pesquisar são passados no formato 'chave;valor'.

    Args:
        dictlist (list): lista de dicionários;
        args (string): string contendo o par chave;valor.

    Returns:
        Int com o número de repetições encontradas.
    """
    sum = 0
    arg_list = [arg.strip() for arg in args.split(';')]
    key = arg_list[0]
    value = arg_list[1]

    if isinstance(dictlist, list):
        for dictionary in dictlist:
            for k, v in list(dictionary.items()):
                if k == key and v == value:
                    sum += 1
    return sum


@register.filter
def indice(value, arg):
    """
    Obtem o elemento **arg** da lista/dicionário **value**.

    Args:
        value (list|dict): lista ou dicionário;
        arg (int|string): item a ser retornado.

    Returns
        Elemento da lista|dicionário.
    """
    return value[arg]


@register.filter(name='getattr')
def getattr_(obj, args):
    """
    Tenta obter um atributo de um objeto.

    Args:
        obj (object): objeto base para obter o atributo;
        args (string): nome do atributo.

    Example:
        {% if block|getattr:"editable,True" %}

    Returns:
        Atributo solicitado.

    Try to get an attribute from an object.
    """
    splitargs = args.split(',')
    try:
        (attribute, default) = splitargs
    except ValueError:
        (attribute, default) = args, ''

    try:
        return obj.__getitem__(attribute)
    except Exception:
        pass

    try:
        attr = obj.__getattribute__(attribute)
    except AttributeError:
        attr = obj.__dict__.get(attribute, default) if hasattr(obj, '__dict__') else default
    except Exception:
        attr = default

    if hasattr(attr, '__call__'):
        return attr.__call__()
    else:
        return attr


@register.filter(name='ldap_attr')
def ldap_attr(obj):
    if isinstance(obj, list):
        if len(obj) == 1:
            val = obj[0]
            if val:
                return mark_safe(val)
            else:
                return mark_safe('-')
        else:
            out = ['<ol>']
            for i in obj:
                out.append('<li>%s</li>' % i)
            out.append('</ol>')
            return mark_safe(''.join(out))
    else:
        if obj:
            return mark_safe(obj)
        else:
            return mark_safe('-')


@register.filter(name='getkey')
def getkey(value, arg):
    """
    Obtem o valor de uma chave em um dicionário.

    Args:
        value (dict): dicionário;
        arg (string): chave de pesquisa

    Returns:
        O elemento do dicionário.

    Note:
        O valor padão para chaves não existentes é a string vazia.
    """
    return value.get(arg, '')


@register.filter(name='app_verbosename')
def app_verbosename(value):
    """
    Obtem o nome de uma aplicação.

    Args:
        value (string): nome da aplicação.

    Returns:
        String contendo o nome da aplicação.

    Note:
        O nome é o **verbose_name** da contido em app.py.
    """
    return apps.get_app_config(value).verbose_name or ''


@register.filter(name='method')
def method(obj, method):
    """
    Obtem um método de um objeto.

    Args:
        obj (object): objeto base para obtenção do método;
        method (string): nome do método.

    Returns:
        Método solicitado.
    """
    return obj.__getattribute__(method)


@register.filter(name='call')
def call(obj, args):
    """
    Invoca um método de um objeto.

    Args:
        obj (object): objeto base para invocação do método;
        args (string): nome do método.

    Returns:
        Resultado do método invocado.
    """
    return obj.__call__(args)


@register.filter(is_safe=True)
def in_group(user, group, ignore_if_superuser=True):
    """
    Verifica se o usuário está no grupo(s) passado(s).

    Args:
        user (User): usuário;
        group (string or list): string com o nome do grupo, ou, grupos;
        ignore_if_superuser (bool): indica se é para ignorar se o usuário é **superuser**.

    Examples:
        Usage::
            {% if user|in_group:"GroupX" %}
            or
            {% if user|in_group:"GroupX,A group with white-spaces" %}

    Raises:
        TypeError se o grupo não for uma string ou um iterável.

    Returns:
        True se o usuário estiver no(s) grupo(s) passado(s).

    Notes:
        Para passar mais de um grupo, deve-se separar por virgula.
    """
    if ignore_if_superuser:
        ignore_groups = user.is_superuser
    else:
        ignore_groups = False
    return user.is_authenticated and (ignore_groups or user.has_group(group))


@register.filter
def calc_colspan(max_pairs, pairs):
    """
    Calcula o colspan para um conjunto de pares.

    Args:
        max_pairs ():
        pairs ():

    Returns:
        Inteiro com o cálculo do colspan.
    """
    return 2 * (int(max_pairs) - int(pairs)) + 1


@register.filter
def text_small(value):
    """
    Adiciona a tag **small** a um texto.

    Args:
        value (string): texto a ser colocado na **tag small**.

    Returns:
        String contendo o texto passado em uma **tag small**.
    """
    if value:
        return mark_safe('<small>{}</small>'.format(value))
    else:
        return ''


@register.filter
def status(value, extra_class=''):
    """
    Imprime a **tag span** correspondete ao status de acordo com valor passado.

    Args:
        value: valor a ser analisado;
        extra_class (string): classe **css** extra.

    Returns:
        String contendo **tag span** para o status.
    """
    if value:
        if value is True:
            return mark_safe('<span class="status status-success {}">Sim</span>'.format(extra_class))
        css = to_ascii(str(value).lower().replace(' ', '-'))
        return mark_safe('<span class="status status-{} {}">{}</span>'.format(css, extra_class, value))
    else:
        if value is False:
            return mark_safe('<span class="status status-error {}">Não</span>'.format(extra_class))
        return ''


@register.filter
def normalizar(nome):
    """
    Normaliza um nome.

    Args:
        nome (string): nome a ser normalizado.

    Returns:
         String com o nome normalizado.

    Note:
        O nome passado sai no formato: Fulade de Tal.
    """
    return normalizar_nome_proprio(str(nome))


@register.filter(name='getattrr')
def getattrr(obj, args):
    """
    Obtem um atributo de um objeto.

    Args:
        obj (object): objeto base;
        args (string): nome do atributo.

    Returns:
        Atributo solicitado ou string vazia.
    """
    splitargs = args.split('.')
    try:
        return getattr_rec(obj, splitargs)
    except AttributeError:
        return '-'
    except Exception:
        return '-'


def getattr_rec(obj, args):
    """
    Obtem um atributo de um objeto.

    Args:
        obj (object): objeto base;
        args (string): nome do atributo.

    Returns:
        Atributo solicitado ou string vazia.
    """
    if obj is None:
        return '-'
    if callable(obj):
        obj = obj()
    if len(args) > 1:
        attr = args.pop(0)
        return getattr_rec(getattrr(obj, attr), args)
    else:
        retorno = getattr(obj, args[0])
        if hasattr(retorno, 'all'):
            return ', '.join([str(x) for x in retorno.all()])
        if callable(retorno):
            retorno = retorno()
        return retorno


@register.filter
def subtract(arg1, arg2):
    """
    Realiza a subtração entre dois valores.

    Args:
        arg1: minuendo;
        arg2: subtraendo.

    Returns:
        Valor obtido pela subtração: arg1 - arg2
    """
    if isinstance(arg1, datetime) or isinstance(arg1, date):
        # subtrair arg2 (um inteiro) dia(s) de arg1 (uma data) # no template: {{ data|subtract:1 }}
        return arg1 - timedelta(arg2)
    return arg1 - arg2


@register.filter(name='times')
def times(number):
    """
    Gera uma lista com um **range** de **number**.

    Args:
        number (int): valor a gerar o **range**.

    Returns:
         Lista contendo o **range** de **number**.
    """
    return list(range(number))


@register.filter
def timesince(data, now=None):
    """
    Gera uma string com expressando o número de anos, meses e dias de uma determinanda data, ou período.

    Args:
        data (date|datetime): data inicial para comparação;
        now (date|datetime): data final para comparação.

    Returns:
         String contendo a expressão da quantidade de anos, meses e dias.

    Notes:
        * Se as datas passadas forem do tipo **datetime** será acescentado as horas, minutos e segundos a strig;
        * Se o argumento now não for passado, será considerada a data atual.
    """
    if not data:
        return ""

    is_datetime = isinstance(data, datetime) and ((now and isinstance(now, datetime)) or not now)

    def append_result(result, str_to_append):
        if result:
            result += ', '
        result += str_to_append
        return result

    if not isinstance(data, datetime):
        data = datetime(data.year, data.month, data.day)

    if now and not isinstance(now, datetime):
        now = datetime(now.year, now.month, now.day)

    if not now:
        now = datetime.now()

    if not is_datetime:
        data = data.date()
        now = now.date()

    delta = relativedelta(now, data)
    result = ""

    if delta.years:
        result = append_result(result, '%d ano%s' % (delta.years, pluralize(delta.years, 's')))

    if delta.months:
        result = append_result(result, '%d m%s' % (delta.months, pluralize(delta.months, 'ês,eses')))

    if delta.days:
        result = append_result(result, '%d dia%s' % (delta.days, pluralize(delta.days, 's')))

    if is_datetime:
        if delta.hours:
            result = append_result(result, '%d hora%s' % (delta.hours, pluralize(delta.hours, 's')))

        if delta.minutes:
            result = append_result(result, '%d minuto%s' % (delta.minutes, pluralize(delta.minutes, 's')))

        if delta.seconds and result == '':
            result = append_result(result, '%d segundo%s' % (delta.seconds, pluralize(delta.seconds, 's')))

    return result


@register.filter
def filename(value):
    """
    Obtem o nome do arquivo em disco para um **field** do tipo **File**.

    Args:
        value (FileField): campo do tipo arquivo.

    Returns:
        String com o nome do arquivo em disco.

    Notes:
        Caso não seja encontrado arquivos, será retornada a string "Arquivo não encontrado".
    """
    import os

    try:
        return os.path.basename(value.file.name)
    except Exception:
        return 'Arquivo não encontrado'


@register.filter
def arvore_setor(setor, lista=None):
    """
    Gera a árvore de setores com base em um setor.

    Args:
        setor (Setor): setor base para montagem da árvore;
        l (list):

    Returns:
        String com estrutura, em **HTML**, da árvore de setores.
    """
    if lista is None:
        lista = []
    areas_vinculacao = []
    for area_vinculacao in setor.areas_vinculacao.all():
        areas_vinculacao.append('<div class="tree-tag">%s</div>' % area_vinculacao.descricao)
    destaque = areas_vinculacao and 'negrito' or 'cinza'
    areas_vinculacao = areas_vinculacao and ''.join(areas_vinculacao) or ''
    lista.append('<li><span class="{}">{}</span> {}'.format(destaque, setor, areas_vinculacao))
    if setor.setor_set.exists():
        lista.append('<ul>')
        for subsetor in setor.setor_set.all():
            arvore_setor(subsetor, lista)
        lista.append('</ul>')
    lista.append('</li>')
    return mark_safe(''.join(lista))


@register.filter
def verbose(instance, arg):
    """
    Obtem o **verbose_name** de um field com base em uma instãncia.

    Args:
        instance (Model): instância base para obter o **field**;
        arg (string): nome do **field**.

    Returns:
        String com o **verbose_name**
    """
    return instance._meta.get_field(arg).verbose_name


@register.filter
def order(queryset, request):
    """
    Ordena um queryset com base no atributo **order** contido em GET.

    Args:
        queryset (Queryset): queryset a ser ordenado;
        request (HttpRequest): objeto request.

    Returns:
        QuerySet ordenada.
    """
    if request.GET.get('order'):
        args = [x.strip() for x in request.GET['order'].split(',')]
        return queryset.order_by(*args)
    return queryset


@register.filter()
def value(obj, campo):
    """
    Obtem o valor de um campo em um dicionário.

    Args:
        obj (dict): objeto, dict, para obter o valor;
        campo (string): nome do campo.

    Returns:
        O valor de **campo** em **obj**.
    """
    return obj.get(campo)


@register.filter()
def alias(campo):
    """
    Obtem o **alias** na lista **djtools.choices.campos**.

    Args:
        campo (string): nome do campo.

    Returns:
         String contendo o **alias**.
    """
    for filtro in campos:
        if filtro['campo'] == campo:
            return filtro['alias']
    return campo


@register.filter()
def get_value_dict(dicionario, chave):
    """
    Obtem o valor de um item de dicionário.

    Args:
        dicionario (dict): dicionário base de pesquisa;
        chave (string): chave a ser procurada.

    Returns:
         Valor contido no dicionário no índice chave.
    """
    return dicionario[chave]


@register.filter()
def mascara_dinheiro(valor):
    """
    Coloca a mascará de dinheiro em um valor.

    Args:
        valor (): valor a ser mascarado.

    Returns:
        String com o valor na mascara de dinheiro.
    """
    return mask_money(valor or 0.0)


@register.filter
def mostrar_virgula(value):
    """
    Substitui ponto por virgula.

    Args:
        value (string): texto a ser processado.

    Returns:
         String com o valor passado substituido ponto por vírgula.
    """
    return value.replace('.', ',')


@register.filter()
def latest(obj, campo):
    """
    Obtem o último item do **queryset**.

    Args:
        obj (Queryset): objeto queryset;
        campo (string): nome do campo.

    Returns
        Último elemento do queryset.
    """
    try:
        return obj.latest(campo)
    except Exception:
        return None


@register.filter()
def mask_number(valor):
    """
    Coloca a mascará de dinheiro em um valor.

    Args:
        valor (): valor a ser mascarado.

    Returns:
        String com o valor na mascara de dinheiro.
    """
    return mask_numbers(valor)


@register.filter()
def anonimizar_cpf(cpf):
    """
    Anonimiza CPF.

    Args:
        valor (): valor a ser anonimizado.

    Returns:
        String com o valor anonimizado.
    """
    return anonimizador_cpf(cpf)


@register.filter()
def hora_relogio(hora_aula):
    return math.ceil(Decimal(hora_aula) * Decimal(3) / 4)


@register.filter
def cpf_sem_caracteres(value):
    """
    Obtem o CPF sem mascara.

    Args:
        value (string): string contendo o CPF.

    Returns:
         CPF sem mascara.
    """
    return value.replace('.', '').replace('-', '')


@register.filter
def month_name(month_number):
    """
    Obtem o nome do mês com base em seu valor numérico.

    Args:
        month_number (int): número do mês.

    Returns:
         String contendo o nome do mês.

    Notes:
        É considerado que janeiro equivale ao número 1 e dezembro ao número 12.
    """
    return Meses.get_mes(month_number)


@register.filter
def ordenar_faixas_classificacao(faixas_classificacao):
    if faixas_classificacao.exists():
        lista = []
        d = {}
        for faixa_classificacao in faixas_classificacao:
            d[faixa_classificacao.oferta_vaga.lista.descricao] = faixa_classificacao
        if faixa_classificacao.oferta_vaga.edital.configuracao_migracao_vagas:
            nomes = faixa_classificacao.oferta_vaga.edital.configuracao_migracao_vagas.get_nomes_listas_ordenadas_por_restricao()
            for nome in nomes:
                if nome in d:
                    lista.append(d.pop(nome))
            for faixa_classificacao in list(d.values()):
                lista.append(faixa_classificacao)
            return lista
    return faixas_classificacao


@register.filter
def push_item(lst, item):
    """
    Adiciona um item a uma lista.

    Args:
        l (list): lista;
        item: valor a ser adicionado.

    Returns:
        String vazia.
    """
    lst.append(item)
    return ''


@register.filter(name='range')
def _range(_min, args=None):
    """
    Obtem um **range**.

    Args:
        _min (int): valor mínimo do range;
        args: valor máximo e passo.

    Returns:
        Lista contendo os elementos de um range.
    """
    _max, _step = None, None
    if args:
        if not isinstance(args, int):
            _max, _step = list(map(int, args.split(',')))
        else:
            _max = args
    args = [_f for _f in (_min, _max, _step) if _f]
    return list(range(*args))


@register.filter(is_safe=True)
def getobjectfieldbyid(value, args):
    """
    Obtem um objeto com base no nome completo da classe.

    Args:
        value (int): id do objeto;
        args (string): nome completo da classe.

    Returns:
        Objeto com base na classe e valor passado.

    Notes:
        O nome completo é no formato aplicação.modelo.campo.
    """
    from django.apps import apps

    app, model, field = args.split(',')
    model = apps.get_model(app, model)
    return model.objects.get(id=value).__getattribute__(field)


@register.filter
def collapse_if_true(value):
    """
    Obterm a classe (CSS) para colapsar.

    Args:
        value (): valor a ser considerado.

    Returns:
         String 'collapsed'se algum valor em **value** for passado.
    """
    return 'collapsed' if bool(value) else ''


@register.filter
def getextfrompath(path):
    """
    Obtem a extensão de um arquivo.

    Args:
        path (string): string contendo o **path** completo do arquivo.

    Returns:
        String contendo a extensão do arquivo.
    """
    return os.path.splitext(path)[1]


@register.filter
def por_extenso(value):
    """
    Obtem o extenso de um valor.

    Args:
        value (): valor a ser escrito.

    Returns:
         String que expressa **value** por extenso.
    """
    if bool(value):
        reais, centavos = str(value).split('.')
        return '{}'.format(extenso(reais, centavos))
    else:
        return '-'


@register.filter
def tem_atributo(obj, value):
    """
    Verifica se o atributo indicado em **value** existe em **obj**.

    Args:
        obj (object): objeto base para pesquisa;
        value (string): nome do atributo.

    Returns:
        True se o elemento existir.
    """
    return hasattr(obj, value)


@register.filter
def somar(valor1, valor2):
    """
    Obtem a soma de dois valores.

    Args:
        valor1: primeiro valor;
        valor2: segundo valor.

    Returns:
         A soma dos dois valores.
    """
    return valor1 + valor2


@register.filter
def dividir_inteiro(valor1, valor2):
    """
    Obtem a divisão entre dois valores arredondando para baixo de dois valores.

    Args:
        valor1: primeiro valor;
        valor2: segundo valor.

    Returns:
         A soma dos dois valores.
    """
    try:
        return int(valor1) // int(valor2)
    except (ValueError, ZeroDivisionError):
        return None


@register.filter
def count_first_queryset(d):
    """
    Conta os elementos da primeiro queryset do dicionário passado.

    Args:
        d (dict): dicionário.

    Returns:
        Inteiro contendo o número de elementos do primeiro queryset.
    """
    lista = [*d.values()]
    return lista and lista[0].count() or 0


@register.filter
def tratar_parametros_filter(url, parametro):
    """
    Trata a "**query string**" passada tranformando no padrão chave=valor.

    Args:
        url (string): string contendo a **query string**;
        parametro (string): parametro a ser retornado.

    Returns:
        String contendo o parametro solicitado.
    """
    for valor in url.replace('?', '').split('&'):
        parametros = valor.split('=')
        if len(parametros) > 1 and parametro == parametros[0]:
            return f'{parametros[0]}={parametros[1]}'
    return ''


@register.filter
def retirar_parametro_get(url, parametros):
    """
    Trata a "**query string**" passada retirando as chaves passadas.
    Exemplo:
    def retirar_parametro_get('?setor=1&campus=2&tab=2', 'setor,tab'):
        return '&campus=2'


    Args:
        url (string): string contendo a **query string**;
        parametros (string): parametros separados por ',' a serem retirados.

    Returns:
        String contendo o parametro solicitado.
    """
    retorno = ''
    parametros = parametros.split(',')
    for valor in url.replace('?', '').split('&'):
        if valor:
            url_param = valor.split('=')
            if len(url_param) and not url_param[0] in parametros:
                valor = ''
                if len(url_param) > 1:
                    valor = url_param[1]
                retorno += f'&{url_param[0]}={valor}'
    return retorno


@register.filter()
def base64encode(val):
    return base64.b64encode(val.encode()).decode()


@register.filter()
def base64decode(val):
    return base64.b64decode(val.encode()).decode()


@register.filter
def safe_message(message):
    return message.message if isinstance(message.message, SafeText) else escape(message.message)


@register.filter('int')
def integer(a):
    return int(a)


@register.filter
def multiply(a, b=1):
    return a * b


@register.filter
def checkbox_input(obj, checked=False):
    return '<input type="checkbox" value="{}" name="item_{}" id="item_{}" title="{}" {} style="margin-right:10px"/>'.format(
        obj.pk, obj.pk, obj.pk, obj, 'checked' if checked else ''
    )


@register.filter
def radio_input(obj, checked=False):
    return '<input type="radio" value="{}" name="item" id="item_{}" title="{}" {} style="margin-right:10px"/>'.format(
        obj.pk, obj.pk, obj, 'checked' if checked else ''
    )


@register.filter
def input_label(obj):
    return '<label for="item_{}">{}</label>'.format(obj.pk, obj)


@register.filter
def formatar_nota(nota):
    if nota is None:
        nota = ''
    else:
        nota = mask_nota(nota)
    return nota
