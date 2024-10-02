import json
import tempfile
from functools import WRAPPER_ASSIGNMENTS
from functools import wraps

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.forms import BaseForm
from django.http import HttpResponse, HttpResponseRedirect, HttpRequest
from django.shortcuts import render as django_render
from django.template import Template, Context, TemplateDoesNotExist

from .breadcrumbs import breadcrumbs_add, breadcrumbs_previous_url
from .http import is_ajax
from .email import send_mail
from .python import get_app_name
from .tl import get_tl
from django.template.loader import select_template, get_template

__all__ = ['httprr', 'get_template_path', 'render', 'rtr', 'render_from_string', 'render_html_file', 'XmlResponse', 'JsonResponse', 'PDFResponse', 'apagar_chave_sessao', 'render_to_string']


def httprr(url, message='', tag='success', anchor='', get_params='', close_popup=False):
    """
    Shortcut para o **HttpResponseRedirect** que possibilita a passagem de uma mensagem.

    Args:
        url (string): string com a url a redirecionar;
        message (string): string contendo a mensagem a ser passada;
        tag (string): tag utilizada para caracterizar a mensagem, por exemplo: success, warning
        anchor (string): ancora a ser direcionado a página;
        get_params (string): contem pares chave=valor, por exemplo: 'p1=v1&p2=v2';
        close_popup (bool): instrui fechar imediatamente janela de popup se esse for o caso.

    Returns:
        Objeto HttpResponseRedirect, ou HttpResponse quando for para fechar janelas popups.
    """

    def set_message():
        if message:
            from django.contrib import messages
            if tag == 'success':
                messages.success(request, message)
            elif tag == 'warning':
                messages.warning(request, message)
            else:
                messages.error(request, message, extra_tags='errornote')

    request = get_tl().get_request()

    tab = 'tab' in request.GET and request.GET['tab'] and '?tab=%s' % request.GET['tab'] or ''

    if get_params:
        get_params = '{}{}'.format(tab, get_params)
        if not get_params[0] == '?':
            get_params = '?{}'.format(get_params.replace('?', ''))

    if close_popup and '_popup' in request.GET.keys():
        if '_popup_close_noreload' in request.GET.keys():
            return HttpResponse(f'<script>parent.close_fancybox_noreload("{message}", "{tag}");</script>')
        else:
            # reload por padrão
            set_message()
            return HttpResponse('<script>parent.close_fancybox();</script>')

    if url == '..' and (tag == 'success' or tag == 'warning' or tag == 'error') and '_popup' in request.GET.keys():
        if '_popup_close_noreload' in request.GET.keys():
            return HttpResponse(f'<script>parent.close_fancybox_noreload("{message}", "{tag}");</script>')
        else:
            # reload por padrão
            set_message()
            return HttpResponse('<script>parent.close_fancybox();</script>')

    set_message()

    if url == '.':
        url = '{}{}'.format(request.path, get_params)
    elif url == '..':
        url = breadcrumbs_previous_url(request)

    url = anchor and '{}#{}'.format(url, anchor) or url

    return HttpResponseRedirect(url)


def get_template_path(function):
    """
    Obtem o template, a renderizar, com base em uma função.

    Args
        function (Function): função.

    Returns:
        String com o template a ser renderizado.
    """
    app_name = get_app_name(function)
    if app_name == settings.PROJECT_NAME:
        return 'templates/%s.html' % (function.__name__)
    return '{}/templates/{}.html'.format(app_name, function.__name__)


def render(template_name, ctx=None, request=None):
    """
    Especialização para o shortcut "*render*" que introduz informação do RequestContext no contexto.

    Args:
        template_name (string): string com o nome do template a renderizar;
        ctx (dict): dicionário contendo o contexto passado ao template;
        request (HttpRequest): objeto request.

    Returns:
        HttpResponse com template renderizado.
    """
    DEFAULT_TEMPLATE = 'djtools/templates/default.html'
    if not request or not hasattr(request, 'user'):
        request = get_tl().get_request()

    ctx = ctx or dict()

    # Adiciona os media dos forms nesta variável do contexto para colocar as medias deles no html HEAD
    forms_media = ""
    for value in list(ctx.values()):
        if isinstance(value, BaseForm):
            media = str(value.media)
            if media not in forms_media:
                forms_media += media

    ctx["forms_media"] = forms_media

    # Breadcrumbs
    if request and (not is_ajax(request) and 'two_factor_authentication' not in request.path):
        breadcrumbs_add(request, ctx)

    # Renderizando
    try:
        return django_render(request, template_name, ctx)
    except TemplateDoesNotExist:
        return django_render(request, DEFAULT_TEMPLATE, ctx)


def rtr(template=None, two_factor_authentication=False):
    """
    Decorator que adiciona renderização a uma função/view.

    Args:
        template (string): nome do template para renderizar.

    Returns:
        Função decorada.

    Note:
        Caso não seja passado o nome de um template, o template será calculado com base em *get_template_path*
    """

    def receive_function(function):
        @wraps(function, assigned=WRAPPER_ASSIGNMENTS)
        def receive_function_args(request, *args, **kwargs):
            if two_factor_authentication and not request.session.get('2fa') and not settings.DEBUG:
                if not request.user.is_authenticated:
                    return httprr('..', 'Por favor efetue o login novamente.')
                if not request.user.get_vinculo().pessoa.email_secundario:
                    return httprr('..', 'Esta funcionalidade requer o envio de um código de autenticação para o seu e-mail secundário, porém, você não possui este e-maill cadastrado. Entre em contato com o setor de Gestão de Pessoas da sua unidade para cadastro do seu email.', 'error')
                from djtools.models import TwoFactorAuthenticationCode
                obj = TwoFactorAuthenticationCode.objects.create()
                send_mail('[SUAP] Código de Autenticação', '<h1>Código de Autenticação</h1><dl><dt>Código:</dt><dd>{}</dd></dl><div class="clear"></div><p>Você não deve compartilhar este código com terceiros.</p>'.format(
                    obj.code), settings.DEFAULT_FROM_EMAIL, [request.user.get_vinculo().pessoa.email_secundario])
                url = '/djtools/two_factor_authentication/?next={}'.format(
                    request.path)
                if '_popup' in request.GET:
                    url = '{}&_popup=1'.format(url)
                return HttpResponseRedirect(url)
            f_return = function(request, *args, **kwargs)
            if isinstance(f_return, HttpResponse):
                return f_return
            app_name = get_app_name(function)
            if isinstance(request, HttpRequest):
                request.help_key = '{}.{}'.format(app_name, function.__name__)
            template_list = [template or get_template_path(function)]
            if settings.LPS:
                if template:
                    template_name_lps = '{}/lps/{}/templates/{}'.format(
                        app_name, settings.LPS, template.split('/')[-1])
                else:
                    template_name_lps = '{}/lps/{}/templates/{}.html'.format(
                        app_name, settings.LPS, function.__name__)
                template_list.insert(0, template_name_lps)
            return render(template_list, f_return, request)

        return receive_function_args

    return receive_function


def render_from_string(message, dictionary):
    template = Template(message)
    context = Context(dictionary)
    return template.render(context)


def render_html_file(html, dicionario, request, task):
    dicionario['menu_as_html'] = request.session.get('menu_as_html', '')
    dicionario['debug'] = settings.DEBUG
    tmp = tempfile.NamedTemporaryFile(suffix='.html', mode='w+b', delete=False)
    tmp.write(render(html, dicionario, request=request).content)
    tmp.close()
    return task.finalize('Relatório gerado com sucesso.', '..', file_path=tmp.name)


class XmlResponse(HttpResponse):

    def __init__(self, data):
        HttpResponse.__init__(self, content=data, content_type='application/xhtml+xml')


class JsonResponse(HttpResponse):
    """
    Classe derivada do **HttpResponse** que retorna um conteúdo do tipo '*application/json*'.
    """

    def __init__(self, data):
        """
        Construtor da classe.

        Args:
            data (dict): dict com os dados do conteúdo.
        """
        content = json.dumps(data, cls=DjangoJSONEncoder)
        HttpResponse.__init__(self, content=content, content_type='application/json')

    @staticmethod
    def invalid(message, field_name=None, field_index=None):
        """
        Método estático para conteúdo invalido.

        Args:
            message (string): mensagem a ser passada;
            field_name (string): nome do campo;
            field_index (): .

        Note:
            O argumento message deve ser Unicode, caso não seja, será convertida.
        """
        if not isinstance(message, str):
            message = message.decode('utf-8')
        return JsonResponse({'valid': False, 'field_name': field_name, 'field_in_list': field_index is not None, 'field_index': field_index, 'message': message})

    @staticmethod
    def valid(args=None, message=None):
        """
        Método estático para conteúdo válido.

        Args:
            args (): ;
            message (string): mensagem a ser passada.
        """
        data = {'valid': True}
        if args:
            for key in args:
                data[key] = args[key]
        if message:
            data['message'] = message
        return JsonResponse(data)


class PDFResponse(HttpResponse):
    """
    Classe derivada do **HttpResponse** que retorna um conteúdo do tipo '*application/pdf*'.
    """

    def __init__(self, data, nome='relatorio.pdf', anexo=True):
        """
        Construtor da classe.

        Args:
            data (byte): conteúdo a ser processado;
            nome (string): nome do arquivo;
            anexo (bool): indica que o conteúdo deve ser anexado.
        """
        HttpResponse.__init__(self, content=data, content_type='application/pdf')
        if anexo:
            self['Content-Disposition'] = 'attachment; filename=%s' % (nome)


@login_required
def apagar_chave_sessao(request, chave):
    """
    Remove a chave da sessão.
    Útil para remover dicionário de dados dos relatórios.

    Args:
        request (HttpRequest): objeto request;
        chave (string): chave a ser removida.

    Returns:
        Objeto HttpResponse com a mensagem de remoção da chave.
    """
    if chave in request.session:
        del request.session[chave]
    return HttpResponse('Chave %s removida com sucesso.' % (chave))


def render_to_string(template_name, context=None, request=None, using=None):
    """
    Load a template and render it with a context. Return a string.

    template_name may be a string or a list of strings.
    """
    # verificando se existe lps
    lps_context = context.pop("lps_context", None)
    if settings.LPS and lps_context and "nome_modulo" in lps_context.keys():
        try:
            # verificando o template path para recuperar o nome do arquivo
            t_split = template_name.split("/")
            if t_split and isinstance(t_split, list) and t_split[-1] != '':
                template_file = t_split[-1]
            else:
                raise TemplateDoesNotExist("O template não pode ser encontrado.")

            # montando a url do template lps
            app_name = lps_context.get("nome_modulo")
            template_name_lps = "{}/lps/{}/templates/{}".format(app_name, settings.LPS, template_file)

            # se existir diretório extra dentro do diretorio de template
            if "extra_dir" in lps_context.keys():
                # montando a url do template lps
                extra_dirs = lps_context.get("extra_dir")
                template_name_lps = "{}/lps/{}/templates/{}/{}".format(app_name, settings.LPS, extra_dirs, template_file)

            # verificando se o template existe, provocando o TemplateDoesNotExist caso o template não exista
            get_template(template_name_lps)
            # se o template existir, setamos o template_name para o novo endereço
            template_name = template_name_lps
        except TemplateDoesNotExist:
            # caso dê erro no get_template, não é necessário intervenção alguma
            pass

    if isinstance(template_name, (list, tuple)):
        template = select_template(template_name, using=using)
    else:
        template = get_template(template_name, using=using)
    return template.render(context, request)
