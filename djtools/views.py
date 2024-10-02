import os
import urllib.request
import urllib.error
import urllib.parse
from os.path import isfile

import datetime

import magic
from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.decorators import permission_required, login_required
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.db.models.manager import Manager
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.crypto import get_random_string
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
from pycpfcnpj import cpfcnpj

from comum.models import GerenciamentoGrupo, User
from comum.utils import get_setor, get_uo
from djtools import HELP_XML_CONTENTS, tasks
from djtools.choices import GENDER
from djtools.forms import AtribuirPermissaoForm, NotificacaoGrupoForm, TwoFactorAuthenticationForm
from djtools.management.permission import GroupPermission
from djtools.models import Task
from djtools.templatetags.filters import in_group
from djtools.utils import httprr, rtr, has_delete_permission, normalizar_nome_proprio, SuapProcess, \
    timeless_load_qs_query, JsonResponse
from djtools.storages.utils import download_temporary_content
from rh.models import PessoaFisica, Pessoa
from django.db.models.sql.query import Query


def get_artigo(model, singular=True, definido=True):
    key = f'{model._meta.app_label}.{model.__name__}'
    model_gender = GENDER.get(key, 'M')
    if model_gender == 'F':
        if definido:
            model_artigo = singular and 'a' or 'as'
        else:
            model_artigo = singular and 'uma' or 'umas'
    else:
        if definido:
            model_artigo = singular and 'o' or 'os'
        else:
            model_artigo = singular and 'um' or 'uns'
    return model_artigo


def get_pronome(model, singular=True):
    key = f'{model._meta.app_label}.{model.__name__}'
    model_gender = GENDER.get(key, 'M')
    model_artigo = ''
    if model_gender == 'F':
        model_artigo = singular and 'da' or 'das'
    elif model_gender == 'M':
        model_artigo = singular and 'do' or 'dos'
    return model_artigo


def get_item(request, app, view, detail=False):
    view_name = view.replace('change_', '').replace('add_', '')
    if view_name != view:
        model = apps.get_model(app, view_name)
        model_admin = model in admin.site._registry and admin.site._registry[model] or None
    else:
        model = None
        model_admin = None

    if model:
        action = view.startswith('change_') and 'Listar' or view.startswith('add_') and 'Adicionar' or view
        name = f'{action} {model._meta.verbose_name}'
        tip = None
        filters = ''
        if action == 'Listar':
            description = f'''<p>Esta funcionalidade tem por objetivo listar {get_artigo(model, False)}
                                {model._meta.verbose_name_plural.lower()} cadastrad{get_artigo(model, False)}
                                no sistema.</p>'''
            search_fields = []
            if model_admin:
                for i, search_field in enumerate(model_admin.search_fields):
                    if '__' not in search_field:
                        field_name = model._meta.get_field(search_field).verbose_name.lower()
                        if i == 0:
                            search_fields.append(f'<span class="italico">{field_name}</span>')
                        elif i == len(model_admin.search_fields) - 1:
                            search_fields.append(f' e <span class="italico">{field_name}</span>')
                        else:
                            search_fields.append(f', <span class="italico">{field_name}</span>')
                    else:
                        related_class = model
                        related_fields = []
                        for j, field in enumerate(search_field.split('__')):
                            field_name = getattr(related_class._meta.get_field(field), 'verbose_name', str(related_class._meta.get_field(field))).lower()
                            if 'user' in related_class._meta.__str__().lower() and field == 'pessoafisica':
                                related_class = PessoaFisica
                            else:
                                related_class = hasattr(related_class._meta.get_field(field), 'related_model') and related_class._meta.get_field(field).related_model or ''
                            if j == len(search_field.split('__')) - 1:
                                if i == 0:
                                    search_fields.append('f<span class="italico">{field_name}</span>')
                                elif i == len(model_admin.search_fields) - 1:
                                    search_fields.append(f' e <span class="italico>"{field_name}</span>')
                                else:
                                    search_fields.append(f', <span class="italico">{field_name}</span>')
                            else:
                                pronome = get_pronome(related_class)
                                related_fields.insert(0, f' {pronome} <span class="italico">{field_name}</span>')

                        search_fields = search_fields + related_fields
                if search_fields:
                    filters = f'''<p>Através do filtro de <b>Texto</b> , é possível buscar
                            {get_artigo(model, False)} {model._meta.verbose_name_plural.lower()}
                            através do(s) seguinte(s) campo(s): {''.join(search_fields)}.'''
                    if model_admin.avoid_short_search:
                        filters += f'''
                        As preposições "da", "de", "di", "do", "du", "das", "dos", "e" e termos com tamanho menor que 3
                        caracteres são desconsiderados na busca. O resultado é paginado e apenas <span class="italico">{model_admin.list_per_page}
                        registros</span> são listados por vez. Para visualizar outros
                        registros, navegue clicando no link da página contendo seu respectivo número.</p>'''
        else:
            description = f'<p>Esta funcionalidade tem por objetivo adicionar {get_artigo(model, False)} {model._meta.verbose_name_plural.lower()} no sistema.</p>'
            tip = f'clique no botão "{name}" localizado no canto superior direito da tela.'

        groups = []
        for group in Group.objects.filter(permissions__codename=view, permissions__content_type__app_label=app).distinct():
            groups.append(group.name)

        required_to = []
        required_models = []
        actions = []
        if detail and action == 'Adicionar':
            get_all_related_objects_with_model = [
                (f, f.model if f.model != model else None) for f in model._meta.get_fields() if (f.one_to_many or f.one_to_one) and f.auto_created and not f.concrete
            ]

            for relation in get_all_related_objects_with_model:
                if relation[0].related_model in admin.site._registry:
                    add_permission = f"add_{relation[0].related_model.__name__.lower()}"
                    app_label = relation[0].related_model._meta.app_label
                    if request.user.has_perm(f"{app_label}.{add_permission}"):
                        sub_item = get_item(request, app_label, add_permission)
                        if sub_item and sub_item['groups'] and sub_item not in required_to:
                            required_to.append(sub_item['view'])

            if model_admin:
                form = model_admin.get_form(request)()
                for field in model_admin.model._meta.fields:
                    if hasattr(field.remote_field, 'model') and field.remote_field.model != model:
                        required_models_string = '{} {}'.format(field.remote_field.model._meta.verbose_name, (field.null or field.blank) and '(Opcional)' or '')
                        if not required_models_string in required_models and not required_models_string.startswith('User'):
                            required_models.append(required_models_string)
                for field_name in form.base_fields:
                    field = form.fields[field_name]
                    if hasattr(field.widget, 'choices') and hasattr(field.widget.choices, 'queryset'):
                        required_models_string = '{} {}'.format(field.widget.choices.queryset.model._meta.verbose_name, not field.required and '(Opcional)' or '')
                        if not required_models_string in required_models and not required_models_string.startswith('User'):
                            required_models.append(required_models_string)
                for inline in model_admin.inlines:
                    for field in inline.model._meta.fields:
                        if hasattr(field.remote_field, 'model') and field.remote_field.model != model:
                            required_models_string = '{} {}'.format(field.remote_field.model._meta.verbose_name, (field.null or field.blank) and '(Opcional)' or '')
                            if not required_models_string in required_models and not required_models_string.startswith('User'):
                                required_models.append(required_models_string)
                for pai in model_admin.model._meta.get_parent_list():
                    for field in pai._meta.fields:
                        if hasattr(field.remote_field, 'model') and field.remote_field.model != model:
                            required_models_string = '{} {}'.format(
                                normalizar_nome_proprio(field.remote_field.model._meta.verbose_name),
                                (field.null or field.blank) and '(Opcional)' or '',
                            )
                            if not required_models_string in required_models and not required_models_string.startswith('User'):
                                required_models.append(required_models_string)

                actions.append(
                    dict(
                        view=None,
                        name='Salvar',
                        description=f'Salva {get_artigo(model)} {model._meta.verbose_name.lower()} no sistema e retorna para a página anterior.',
                        groups=groups,
                        url=None,
                        tip='clique no botão "Salvar" localizado abaixo do formulário.',
                    )
                )
                actions.append(
                    dict(
                        view=None,
                        name='Salvar e Adicionar Outro(a)',
                        description='Salva %s %s no sistema e limpa o formulário para que mais %s %s possa ser cadastrada.'
                        % (get_artigo(model), model._meta.verbose_name.lower(), get_artigo(model, True, False), model._meta.verbose_name.lower()),
                        groups=groups,
                        url=None,
                        tip='clique no botão "Salvar e adicionar outro" localizado abaixo do formulário.',
                    )
                )
                actions.append(
                    dict(
                        view=None,
                        name='Salvar e Continuar Editando',
                        description='Salva %s %s no sistema e continua na mesma página para que uma nova \
                                    alteração seja realizada, se necessário.'
                        % (get_artigo(model), model._meta.verbose_name.lower()),
                        groups=groups,
                        url=None,
                        tip='clique no botão "Salvar e continuar editando" localizado abaixo do formulário.',
                    )
                )

        if detail and action == 'Listar':
            add_permission = f"add_{model.__name__.lower()}"
            if request.user.has_perm(f"{app}.{add_permission}"):
                sub_item = get_item(request, app, add_permission)
                if sub_item and sub_item['groups']:
                    actions.append(sub_item)
            if model_admin and hasattr(model_admin, 'export_to_xls') and model_admin.export_to_xls:
                actions.append(dict(view='admin.exportar_xls'))

        url = f'/djtools/help_view/{app}/{view}/'
        default = dict(
            view=f'{app}.{view}',
            name=name,
            description=mark_safe(description),
            filters=mark_safe(filters),
            groups=groups,
            url=url,
            actions=actions,
            required_to=required_to,
            required_models=required_models,
            detail='',
            conditions=[],
            tip=tip,
        )

        help_key = f'{app}.{view}'
        item = help_key in HELP_XML_CONTENTS and HELP_XML_CONTENTS[help_key] or None
        if item:
            for key in item:
                if item[key] and item[key] != 'None':
                    if default[key].__class__ == list:
                        default[key] += item[key]
                    else:
                        if key == 'description' and action == 'Listar':
                            default[key] = '{}{}'.format(item[key], '</p>'.join(default[key].split('</p>')[1:]))
                        else:
                            default[key] = item[key]
        return default
    else:
        help_key = f'{app}.{view}'
        item = help_key in HELP_XML_CONTENTS and HELP_XML_CONTENTS[help_key] or None
        return item


@login_required
@rtr()
def help_view(request, app, view):
    item = get_item(request, app, view, True)
    if item:
        title = 'Ajuda: %s' % item['name']
        actions = []
        for action in item['actions']:
            if action.__class__ == dict and len(list(action.keys())) > 2:
                sub_item = action
            else:
                sub_item = action['view'] in HELP_XML_CONTENTS and HELP_XML_CONTENTS[action['view']] or None
                if 'tip' in action:
                    sub_item['tip'] = action['tip']
            if sub_item:
                if not sub_item.get('groups'):
                    sub_item['groups'] = item['groups']
                actions.append(sub_item)
        required_to = []
        for ref in item['required_to']:
            required_app, required_view = ref.split('.')
            if '#' in ref:
                sub_item = ref in HELP_XML_CONTENTS and HELP_XML_CONTENTS[ref] or None
            else:
                sub_item = get_item(request, required_app, required_view)
            if sub_item:
                required_to.append(sub_item)

    return locals()


def delete_object(request, app, model, pk):
    """
    View genérica para remover um objeto de modelo.
    -----
    Parâmetro opcional no GET: ``redirect_url``.
    """

    # Pegando a classe de modelo e o objeto
    model_class = apps.get_model(app, model)
    obj = get_object_or_404(model_class, pk=pk)

    if not has_delete_permission(obj=obj, user=request.user):
        raise PermissionDenied()

    # Removendo o objeto
    obj.delete()

    # redirect_url
    if 'redirect_url' in request.GET:
        redirect_url = request.GET['redirect_url']
    else:
        redirect_url = request.META.get('HTTP_REFERER', '/')

    # msg
    msg_args = dict(name=model_class._meta.verbose_name.title(), obj=str(obj))
    msg = '%(name)s "%(obj)s" foi removido com sucesso.' % msg_args

    return httprr(redirect_url, msg)


@rtr()
@login_required()
@permission_required('auth.can_change_user')
def give_permission(request):
    if not request.user.is_superuser:
        raise PermissionDenied()
    elif request.method == 'POST' and 'confirmacao' not in request.POST:
        form = AtribuirPermissaoForm(data=request.POST)
        if form.is_valid():
            usuarios = form.cleaned_data['usuarios']
            usuarios = usuarios.replace(',', ';').replace('\r\n', ';')
            grupos = form.cleaned_data['grupos']
            permissoes = form.cleaned_data['permissoes']
            lista_usuarios = []
            lista_usuarios_nao_identificados = []
            for login in usuarios.split(';'):
                if login:
                    login = login.strip()
                    usuario_qs = User.objects.filter(username=login)
                    if usuario_qs:
                        lista_usuarios.append(usuario_qs[0])
                    else:
                        lista_usuarios_nao_identificados.append(login)
            lista = []
            for usuario in lista_usuarios:
                lista.append(str(usuario.pk))
            usuarios_str = ';'.join(lista)
            lista = []
            for grupo in grupos:
                lista.append(str(grupo.pk))
            grupos_str = ';'.join(lista)
            lista = []
            for permissao in permissoes:
                lista.append(str(permissao.pk))
            permissoes_str = ';'.join(lista)
    elif request.method == 'POST' and 'confirmacao' in request.POST:
        form = AtribuirPermissaoForm()
        usuarios_str = request.POST['usuarios']
        grupos_str = request.POST['grupos']
        permissoes_str = request.POST['permissoes']

        grupos = []
        for id in grupos_str.split(';'):
            if id:
                grupos.append(Group.objects.get(pk=id))
        permissoes = []
        for id in permissoes_str.split(';'):
            if id:
                permissoes.append(Permission.objects.get(pk=id))
        for id in usuarios_str.split(';'):
            usuario = User.objects.get(pk=id)
            for grupo in grupos:
                usuario.groups.add(grupo)
            for permissao in permissoes:
                usuario.user_permissions.add(permissao)
            usuario.save()
        httprr("/djtools/give_permission/", 'Permissões atribuídas com sucesso')
    else:
        form = AtribuirPermissaoForm()
    return locals()


def breadcrumbs_reset(request, menu_item_id, url):
    query_string = request.META.get('QUERY_STRING', '')
    if query_string:
        url += f'?{query_string}'
    bc = [['Início', '/']]
    request.session['bc'] = bc
    request.session['menu_item_id'] = menu_item_id
    return HttpResponseRedirect(f'/{url}')


@rtr()
def notificar_grupo(request, pk_grupo):
    title = 'Enviar Mensagem para Grupo'
    grupo = Group.objects.get(pk=pk_grupo)
    gd = grupo.groupdetail_set.first()
    if gd:
        redirect_url = f'/comum/gerenciamento_grupo/?modulo={gd.app}&grupo={grupo.pk}'
    else:
        redirect_url = '/comum/gerenciamento_grupo/'

    print(redirect_url)

    if not GerenciamentoGrupo.user_can_manage(request.user):
        raise PermissionDenied()

    if request.method == 'POST':
        form = NotificacaoGrupoForm(request.POST, request=request)
        if form.is_valid():
            titulo = form.cleaned_data['titulo']
            remetente = form.cleaned_data['remetente']
            texto = form.cleaned_data['texto']
            return tasks.notificar_usuarios_grupo(titulo, remetente, texto, grupo, redirect_url)
    else:
        form = NotificacaoGrupoForm(request=request)
    return locals()


@rtr()
@login_required()
def permissions(request, app):
    if not request.user.is_superuser:
        raise PermissionDenied()
    title = 'Permissões por Grupo'
    groupPermission = GroupPermission(app)
    permissionFileName = f'{app}/permissions.yaml'

    if settings.LPS:
        permissionFileName_lps = f'{app}/lps/{settings.LPS}/permissions.yaml'
        if isfile(permissionFileName_lps):
            permissionFileName = permissionFileName_lps

    groupPermission.processar_yaml(permissionFileName, app)
    groups = groupPermission.groups

    data = []
    for permission in Permission.objects.filter(content_type__app_label=app):
        permission.groups = []
        permission.verbose_name = permission.name.replace('Can add', 'Adicionar').replace('Can change', 'Editar').replace('Can delete', 'Remover')
        for group in groups:
            has_perm = False
            for model in group.getModels():
                for p in model.getPermissions():
                    if permission.codename == p.name:
                        has_perm = True
                        break
            permission.groups.append(has_perm)
        data.append(permission)
    return locals()


@csrf_exempt
@rtr()
def popup_choice_field(request, name, ids=None):
    lista = ids and ids.split(';') or []
    qs = timeless_load_qs_query(request.POST['qs'])
    list_template = request.POST.get('template') or 'popup_choices.html'
    if isinstance(qs, Manager):
        qs = qs.all()

    try:
        titulo = qs.model._meta.verbose_name
    except Exception:
        titulo = 'Opções'

    data = request.GET
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

    for obj in qs:
        obj.checked_ = str(obj.pk) in lista
    return locals()


@csrf_exempt
@rtr()
def popup_multiple_choice_field(request, name, ids=None):
    lista = ids and ids.split(';') or []
    qs_post = request.POST.get('qs', '')
    list_template = request.POST.get('template') or 'popup_multiple_choices.html'
    if not qs_post:
        raise PermissionDenied
    qs = timeless_load_qs_query(qs_post)
    if isinstance(qs, Manager):
        qs = qs.all()
    elif isinstance(qs, Query):
        qs = qs.model.objects.all()

    try:
        titulo = qs.model._meta.verbose_name
    except Exception:
        titulo = 'Opções'

    data = request.GET
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

    for obj in qs:
        obj.checked_ = str(obj.pk) in lista
    return locals()


@rtr()
def process(request, pid, interval=None):
    obj = cache.get(pid)
    if not interval:
        interval = 5000
    if not obj:
        return httprr('/', 'Processo inexistente.', 'error')
    if obj.get('user') != request.user.username:
        return httprr('/', 'Você não tem permissão para acessar este processamento.', 'error')
    if 'send_email' in request.GET:
        obj['send_email'] = True
        cache.set(pid, obj)
        return httprr('..', mark_safe(f'O resultado do processo <a href="/djtools/process/{pid}">{pid}</a> será enviado por email.'))
    if 'continue' in request.GET:
        return httprr(obj['url'], obj['message'], obj['error'] and 'error' or 'success')
    if 'download' in request.GET:
        return HttpResponseRedirect('/djtools/process_download/{}/{}/'.format(obj['pid'], obj['download']))
    title = '%s' % obj['description']
    return locals()


def process_progress(request, pid):
    process = cache.get(pid)
    if not process:
        return HttpResponse('0')
    message = process['message'] or process['percentual']
    return HttpResponse('%s' % message)


@rtr()
def process2(request, uuid_task):
    from djtools.models import Task
    i = get_object_or_404(Task.objects, uuid=uuid_task)
    if i.user and not request.user == i.user:
        return httprr('/', 'Você não tem permissão para isso.', 'error')
    interval = 5000
    if settings.DEBUG:
        interval = 500
    url = request.META.get('HTTP_REFERER', '/')
    title = f'Tarefa {i.id} - {i.type}'
    if request.GET.get('send_email'):
        i.notify = True
        i.save()
        return httprr('/', mark_safe(f'O resultado do processo <a href="/djtools/view_task/{i.id}/">#{i.id}</a> será enviado por email.'))
    return locals()


def generate_file_response(task):
    try:
        content = download_temporary_content(task.file)
    except Exception:
        return httprr('/', 'Arquivo expirado.', 'error')
    if task.file.endswith('.xls'):
        response = HttpResponse(content, content_type='application/ms-excel')
        response['Content-Disposition'] = 'inline; filename=Relatorio.xls'
    elif task.file.endswith('.xlsx'):
        response = HttpResponse(content, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'inline; filename=Relatorio.xlsx'
    elif task.file.endswith('.zip'):
        response = HttpResponse(content, content_type='application/zip')
        response['Content-Disposition'] = 'inline; filename=Arquivo.zip'
    elif task.file.endswith('.pdf'):
        response = HttpResponse(content, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename=Documento.pdf'
    elif task.file.endswith('.csv'):
        response = HttpResponse(content, content_type='text/csv')
        response['Content-Disposition'] = 'inline; filename=Relatorio.csv'
    elif task.file.endswith('.txt'):
        response = HttpResponse(content, content_type='text/txt')
        response['Content-Disposition'] = 'inline; filename=Relatorio.txt'
    elif task.file.endswith('.html'):
        response = HttpResponse(content)
    elif task.file.endswith('.zip'):
        response = HttpResponse(content, content_type='application/zip')
        response['Content-Disposition'] = 'inline; filename=Arquivo.zip'
    else:
        response = HttpResponse(content, content_type='application/octet-stream')
        response['Content-Disposition'] = 'inline; filename=Arquivo.txt'
    return response


def process_progress2(request, download, uuid_task):
    from djtools.models import Task

    i = get_object_or_404(Task.objects, uuid=uuid_task)
    if i.user and not request.user == i.user:
        return httprr('/', 'Você não tem permissão para isso.', 'error')
    if int(download) and i.file:
        return generate_file_response(i)
    return HttpResponse('{}::{}::{}::{}'.format(i.get_progress(), i.message or '', i.file or '', i.url or ''))


@rtr()
def view_task(request, pk):
    i = get_object_or_404(Task.objects, id=pk)
    title = f'Tarefa #{i.id} - {i.type}'

    data_exclusao = datetime.datetime.now() - datetime.timedelta(days=2)

    if request.user != i.user and not in_group(request.user, 'Desenvolvedor'):
        return httprr('/', 'Você não tem permissão para isso.', 'error')

    if request.GET.get('download'):
        return generate_file_response(i)
    return locals()


def process_download(request, pid, file_type):
    process = cache.get(pid)
    if not process:
        return httprr('/', 'Processo inexistente.', 'error')
    if process.get('user') != request.user.username:
        return httprr('/', 'Você não tem permissão para acessar este processamento.', 'error')
    file_path = process.get('file_path', None)
    if not file_path or not os.path.exists(file_path):
        return httprr('/', 'O arquivo foi removido.', 'error')
    with open(file_path, 'r+b') as f:
        content = f.read()
    if int(file_type) == SuapProcess.ARQUIVO_XLS:
        response = HttpResponse(content, content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename=Relatorio.xls'
    elif int(file_type) == SuapProcess.ARQUIVO_ZIP:
        response = HttpResponse(content, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename=Arquivo.zip'
    elif int(file_type) == SuapProcess.ARQUIVO_PDF:
        response = HttpResponse(content, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=Documento.pdf'
    elif int(file_type) == SuapProcess.ARQUIVO_CSV:
        response = HttpResponse(content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=Relatorio.csv'
    elif int(file_type) == SuapProcess.ARQUIVO_TXT:
        response = HttpResponse(content, content_type='text/txt')
        response['Content-Disposition'] = 'attachment; filename=Relatorio.txt'
    else:
        response = HttpResponse(content, content_type='application/octet-stream')
        response['Content-Disposition'] = 'attachment; filename=Arquivo.txt'
    return response


@rtr()
@login_required()
def user_info(request, user_uuid):
    user = get_object_or_404(User, uuid=user_uuid)
    eh_pessoafisica = eh_aluno = False
    requisitante_eh_aluno = request.user.get_vinculo().eh_aluno()
    if hasattr(user, 'pessoafisica'):
        profile = user.pessoafisica
        eh_pessoafisica = True
        nome_social = None
        if user.get_relacionamento_title().capitalize() == 'Aluno':
            eh_aluno = True
            nome_social = user.get_relacionamento().get_nome_social_composto()
        nome = nome_social or profile.nome
        email = profile.email
        foto = profile.get_foto_75x100_url()
        cargo = user.get_relacionamento_title().capitalize()
        setor = get_setor(user) or ''
        campus = get_uo(user) or ''
    elif hasattr(user, 'pessoajuridica'):
        profile = user.pessoajuridica
        nome = profile.nome
        cnpj = profile.cnpj
    return locals()


@rtr()
@login_required()
def profile_info(request, profile_uuid):
    from comum.models import Vinculo
    pessoa = get_object_or_404(Pessoa, uuid=profile_uuid)
    eh_pessoafisica = eh_aluno = False
    requisitante_eh_aluno = request.user.get_vinculo().eh_aluno()
    if hasattr(pessoa, 'pessoafisica'):
        profile = pessoa.pessoafisica
        if not cpfcnpj.validate(profile.cpf):
            vinculos = Vinculo.objects.filter(pessoa=pessoa)
        else:
            vinculos = Vinculo.objects.filter(pessoa__pessoafisica__cpf=profile.cpf)
        eh_pessoafisica = True
        nome_social = profile.nome_social
        nome = nome_social or profile.nome
        email = profile.email
        foto = profile.get_foto_75x100_url()
    elif hasattr(pessoa, 'pessoajuridica'):
        profile = pessoa.pessoajuridica
        nome = profile.nome
        cnpj = profile.cnpj
    return locals()


@rtr()
@login_required()
def view_email(request):
    title = "Notificação por E-mail"
    import json

    emails = json.load(open('deploy/emails.json'))
    emails_file_path = 'deploy/emails.json'
    os.unlink(emails_file_path)
    return locals()


@login_required()
def consultar_cep(request, cep):
    cep = cep.replace('.', '').replace('-', '')
    if cep.isdigit() and len(cep) == 8:
        try:
            return HttpResponse(urllib.request.urlopen(f'http://api.postmon.com.br/v1/cep/{cep}').read().decode('utf-8'))
        except Exception:
            pass
    return HttpResponse()


@csrf_exempt
def consulta_cep_govbr(request, cep):
    Configuracao = apps.get_model('comum', 'Configuracao')
    from djtools.services import consulta_cep
    cpf_operador = Configuracao.get_valor_por_chave('djtools', 'cpf_operador_api_cep_gov_br')
    return JsonResponse(consulta_cep(cpf_operador, cep))


@rtr()
def two_factor_authentication(request):
    title = 'Autenticação via E-mail'
    # removendo a chave de autenticação por e-mail da seção quando o formulário for aberto
    if request.method == 'GET' and '2fa' in request.session:
        del request.session['2fa']
    if not request.user.is_authenticated:
        return httprr('..', 'Por favor realize o login novamente.')
    form = TwoFactorAuthenticationForm(data=request.POST or None, request=request)
    try:
        if form.is_valid():
            # adicinando a chave de autenticação por e-mail na seção
            request.session['2fa'] = 1
            request.session.save()
            url = request.GET['next']
            if '_popup' in request.GET:
                url = f'{url}?_popup=1'
            return httprr(url, 'Código de autenticação validado com sucesso.')
    except Exception:
        return httprr('/', 'Código de autenticação inválido. Por favor, tente novamente.', 'error')
    return locals()


@login_required()
def private_media(request):
    media = request.GET.get('media', '').strip('/')
    if media.split('/')[0] == 'private-media':
        relative_path = os.path.join('private-media', media.split('/', 1)[1])
    else:
        relative_path = os.path.join('private-media', media)

    if not default_storage.exists(relative_path):
        return httprr('/', 'Arquivo inexistente.', 'error')

    file_name, file_extension = os.path.splitext(relative_path)

    mime = magic.Magic(mime=True)
    try:
        with default_storage.open(relative_path) as f:
            content = f.read()
        content_type = mime.from_buffer(content)
        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename=temp{get_random_string()}{file_extension}'
        return response
    except FileNotFoundError as e:
        if settings.DEBUG:
            raise e
        return httprr('/', 'Arquivo não encontrado.', 'error')
