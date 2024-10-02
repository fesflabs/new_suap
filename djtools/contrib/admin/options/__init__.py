# flake8: noqa
import operator
from wsgiref.util import request_uri
import six
from functools import reduce, update_wrapper, partial

from django import forms
from django.core.exceptions import PermissionDenied, SuspiciousOperation, FieldDoesNotExist
from django.urls import path
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
#
from django.contrib import admin, messages
#
from django.contrib.admin import helpers
from django.contrib.admin.options import csrf_protect_m, InlineModelAdmin, flatten_fieldsets
from django.contrib.admin.utils import lookup_needs_distinct, unquote
from django.contrib.admin.utils import (flatten_fieldsets, unquote)
from django.contrib.admin.checks import InlineModelAdminChecks
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
#
from django.contrib.auth import authenticate
from django.db import models, transaction
from django.db.models.fields.related import ManyToManyField
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.urls import reverse
from django.utils.safestring import mark_safe


from django.forms import ALL_FIELDS
from django.forms.formsets import all_valid
from django.forms.models import BaseModelFormSet, modelformset_factory
from reversion_compare.admin import CompareVersionAdmin

from comum.utils import normalizar_termos_busca
from djtools import tasks, utils
from djtools.contrib.admin import helpers
from djtools.contrib.admin.views import ChangeListPlus
from djtools.db.models import ManyToManyFieldPlus
from djtools.forms.fields import DateFieldPlus, DateTimeFieldPlus, TimeFieldPlus
from djtools.forms.widgets import RegionalDateTimeWidget, RegionalDateWidget, RegionalTimeWidget
from djtools.lps import MetaModelAdminPlus
from djtools.templatetags.filters import status
from djtools.templatetags.tags import edit_object_icon, icon, view_object_icon
from djtools.utils import eval_attr, get_change_permission_for_model, get_search_field, get_view_permission_for_model, httprr
from djtools.utils import is_ajax
from django.forms.models import modelform_defines_fields
from djtools.forms import ModelFormPlus, NonrelatedInlineFormSet, nonrelated_inlineformset_factory


FORMFIELD_OVERRIDES = {
    models.DateTimeField: {'form_class': DateTimeFieldPlus, 'widget': RegionalDateTimeWidget},
    models.DateField: {'form_class': DateFieldPlus, 'widget': RegionalDateWidget},
    models.TimeField: {'form_class': TimeFieldPlus, 'widget': RegionalTimeWidget},
}


class TabularInlinePlus(admin.TabularInline):
    formfield_overrides = FORMFIELD_OVERRIDES

    def get_formset(self, request, obj=None, **kwargs):
        """
        Torna o ``request`` disponível no ``form``.
        """
        FormSetClass = super().get_formset(request, obj, **kwargs)
        FormSetClass.form.request = request
        return FormSetClass


class StackedInlinePlus(admin.StackedInline):
    formfield_overrides = FORMFIELD_OVERRIDES

    @property
    def media(self):
        return forms.Media(css={}, js=[])

    def get_formset(self, request, obj=None, **kwargs):
        """
        Torna o ``request`` disponível no ``form``.
        """
        FormSetClass = super().get_formset(request, obj, **kwargs)
        FormSetClass.form.request = request
        return FormSetClass


class ModelAdminPlus(admin.ModelAdmin, metaclass=MetaModelAdminPlus):
    """
    O ModelAdminPlus foi criado para dar mais funcionalidades ao ModelAdmin.

    Atributos:
    ==========
    - list_display_icons = False
        O link para edição de cada objeto fica sendo um ícone (ao invés de ser o primeiro atributo do list_display)
    - show_count_on_tabs = False
        Mostra a quantidade de registros para cada aba, é obrigatório passa os parâmetro *args e **kwargs tanto no
        método queryset quanto nos métodos das tabs para passar a variável "skip_tab".

    Métodos:
    ========

    get_action_bar(self, request)
    -----------------------------

    get_tabs(self, request)
    -----------------------
    Deve retornar uma lista de strings. Cada string deve corresponder ao nome de um método do ModelAdmin.
    Se get_tabs retornar ``['foo']`` o método ``foo(self, request)`` deve ser implementado.

    export_to_csv(self, request, queryset)
    --------------------------------------
    Deve retornar uma lista de listas. Esse resultado será retornado como um CsvResponse.

    get_action_bar_view(self, request, obj)
    ----------------------------------
    Retorna uma lista de itens a serem exibidor na view do objeto
    """

    # Atributos modificados de ``admin.ModelAdmin``
    change_list_template = 'djtools/templates/adminutils/change_list.html'
    change_form_template = 'djtools/templates/adminutils/change_form.html'
    formfield_overrides = FORMFIELD_OVERRIDES

    # Atributos exclusivos do ``ModelAdminPlus``
    list_display_icons = False
    show_count_on_tabs = False
    show_tab_any_data = True
    export_to_xls = False
    list_xls_display = None
    preserve_filters = True
    # utilizado para filtros em cascata para o campo autocomplete
    list_filter_autocomplete_form_filters = None
    # utilizado para indicar quais filtros permitem multiplas escolhas
    list_filter_multiple_choices = tuple()
    # Configuração que faz o admin ignorar termos com menos de 3 caracteres
    avoid_short_search = True

    add_form = None
    action_form = helpers.ActionForm
    change_form = None
    add_fieldsets = None

    def get_actions(self, request):
        actions = super().get_actions(request)
        try:
            del actions['delete_selected']
        except KeyError:
            pass
        return actions

    @property
    def media(self):
        return forms.Media(css={}, js=[])

    def get_tab_corrente(self):
        return self.request.GET.get('tab', None)

    def show_list_display_icons(self, obj):
        out = []
        icons_html = []

        # Tentando verificar a aba atual que está sendo utilizada no admin. Se existir, tentamos verificar se para a tab
        # corrente foi especificado algum parâmetro para a url que será chamada em cada registro listado no grid.
        current_tab = self.get_tab_corrente()
        view_object_url_complement = None
        if current_tab:
            if hasattr(self, current_tab) and hasattr(getattr(self, current_tab), 'view_object_url_params'):
                view_object_url_complement = getattr(getattr(self, current_tab), 'view_object_url_params')

        if self.has_change_permission(self.request, obj):
            icons_html.append(view_object_icon(obj, view_object_url_complement))
            icons_html.append(edit_object_icon(obj))
        else:
            if self.has_view_permission(self.request, obj):
                icons_html.append(view_object_icon(obj, view_object_url_complement))

        for icon_html in icons_html:
            if icon_html:
                out.append(icon_html)
        return mark_safe(''.join(out))

    show_list_display_icons.short_description = '#'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.search_fields and get_search_field(self.model):
            self.search_fields = (get_search_field(self.model).name,)

    def url_wrap(self, view):
        def wrapper(*args, **kwargs):
            return self.admin_site.admin_view(view)(*args, **kwargs)
        #
        return update_wrapper(wrapper, view)

    def get_changelist(self, request, **kwargs):
        """
        Torna o ``request`` disponível em métodos invocados no changelist admin e utiliza
        a classe ``ChangeListPlus``.
        """
        self.request = request
        return ChangeListPlus

    def get_list_display(self, request):
        """
        Adiciona o método ``show_list_display_icons`` no ``list_display`` se for
        o caso.
        """
        list_display = tuple(self.list_display[:])
        if self.list_display_icons:
            if request.user.has_perm(get_view_permission_for_model(self.model)) or request.user.has_perm(get_change_permission_for_model(self.model)):
                list_display = ('show_list_display_icons',) + list_display
            else:
                self.list_display_links = None

        return list_display

    def get_list_filter(self, request):
        """
        Retira do ``self.list_filter`` os itens presentes no ``self.list_filter_autocomplete``.
        """
        return self.list_filter

    def get_tabs(self, request):
        return []

    def get_view_inlines(self, request):
        return []

    def get_queryset(self, request, manager=None, *args, **kwargs):
        return manager or super().get_queryset(request)

    def get_current_queryset(self, request, *args, **kwargs):
        """
        Retorna o queryset exibido atualmente no changelist e é utilizado na
        ação ``export_to_csv``.
        """
        ChangeList = self.get_changelist(request)
        cl = ChangeList(
            request,
            self.model,
            self.list_display,
            self.list_display_links,
            self.list_filter,
            self.date_hierarchy,
            self.search_fields,
            self.list_select_related,
            self.list_per_page,
            self.list_max_show_all,
            self.list_editable,
            self,
            self.sortable_by,
        )
        return cl.get_queryset(request)

    def get_search_results(self, request, queryset, search_term):
        """
        Returns a tuple containing a queryset to implement the search,
        and a boolean indicating if the results may contain duplicates.
        """
        # Apply keyword searches.
        def construct_search(field_name):
            if field_name.startswith('^'):
                return "%s__istartswith" % field_name[1:]
            elif field_name.startswith('='):
                return "%s__iexact" % field_name[1:]
            elif field_name.startswith('@'):
                return "%s__search" % field_name[1:]
            else:
                return "%s__icontains" % field_name

        use_distinct = False
        termos_busca, termos_retirados = normalizar_termos_busca(search_term, self.avoid_short_search)
        search_terms = termos_busca.split()
        if search_terms:
            search_fields = self.get_search_fields(request)
            if search_fields and search_term:
                orm_lookups = [construct_search(str(search_field)) for search_field in search_fields]
                for bit in search_terms:
                    or_queries = [models.Q(**{orm_lookup: bit}) for orm_lookup in orm_lookups]
                    queryset = queryset.filter(reduce(operator.or_, or_queries))
                if not use_distinct:
                    for search_spec in orm_lookups:
                        if lookup_needs_distinct(self.opts, search_spec):
                            use_distinct = True
                            break

        return queryset, use_distinct

    def has_view_permission(self, request, obj=None):
        return utils.has_view_permission(model=self.model, user=request.user)

    def has_change_permission(self, request, obj=None):
        if obj and hasattr(obj, 'can_change'):
            if not obj.can_change(request.user):
                return False
        perm = utils.has_change_permission(model=self.model, user=request.user)
        if not perm and obj is None:
            perm = self.has_view_permission(request, obj)
        return perm

    def has_delete_permission(self, request, obj=None):
        return utils.has_delete_permission(model=self.model, obj=obj, user=request.user)

    def get_action_bar(self, request, remove_add_button=False):
        items = []

        # Botão para adicionar
        if self.has_add_permission(request) and not remove_add_button:
            items.append(dict(url='add/', label='Adicionar %s' % self.model._meta.verbose_name, css_class='success'))

        # Botão para exportar para CSV
        if hasattr(self, 'export_to_csv'):
            url = request.get_full_path()
            if '?' not in url:
                url = url + '?'
            if not url.endswith('?'):
                url = url + '&'
            url = url + 'export_to_csv=1'
            items.append(dict(url=url, label='Exportar para CSV'))

        if self.export_to_xls:
            url = request.get_full_path()
            if '?' not in url:
                url = url + '?'
            if not url.endswith('?'):
                url = url + '&'
            url = url + 'export_to_xls=1'
            items.append(dict(url=url, label='Exportar para XLS'))

        return items

    @csrf_protect_m
    def changelist_view(self, request, extra_context=None):
        self.request = request

        # Help
        request.help_key = '{}.change_{}'.format(self.model._meta.app_label, self.model.__name__.lower())

        # Chama a função de exportar para CSV
        if 'export_to_csv' in request.GET:
            request.GET._mutable = True
            del request.GET['export_to_csv']
            queryset = self.get_current_queryset(request)
            return tasks.admin_export('csv', queryset, request, self)
        # XLS
        if self.export_to_xls and 'export_to_xls' in request.GET:
            request.GET._mutable = True
            del request.GET['export_to_xls']
            queryset = self.get_current_queryset(request)
            return tasks.admin_export('xls', queryset, request, self)

        more_context = dict(object_tools_items=self.get_action_bar(request), title=self.model._meta.verbose_name_plural, disable_general_tabs=True)
        more_context.update(extra_context or {})
        utils.breadcrumbs_add(request, more_context)
        try:
            retorno = super().changelist_view(request, more_context)
        except SuspiciousOperation as so:
            return httprr('.', f'Você escolheu algum filtro inválido, por favor tente novamente nas opções disponíveis.', 'error')
        if is_ajax(request) and hasattr(retorno, 'context_data'):
            return utils.render('djtools/templates/adminutils/content_main_admin.html', retorno.context_data)
        else:
            return retorno

    def get_fieldsets(self, request, obj=None):
        if not obj and self.add_fieldsets:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        """
        Torna o ``request`` disponível no ``FormClass``.
        """
        defaults = {}

        if obj is None and self.add_form:
            defaults['form'] = self.add_form

        if obj and self.change_form:
            defaults['form'] = self.change_form

        defaults.update(kwargs)

        FormClass = super().get_form(request, obj, **defaults)

        FormClass.request = request
        return FormClass

    @csrf_protect_m
    @transaction.atomic
    def add_view(self, request, form_url='', extra_context=None):
        request.help_key = '{}.add_{}'.format(self.model._meta.app_label, self.model.__name__.lower())
        extra_context = dict(title='Adicionar %s' % self.model._meta.verbose_name)
        utils.breadcrumbs_add(request, extra_context)
        return super().add_view(request, form_url, extra_context)

    @csrf_protect_m
    @transaction.atomic
    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = self.get_object(request, unquote(object_id))
        if obj is None:
            return self._get_obj_does_not_exist_redirect(request, self.model._meta, object_id)

        if not self.has_change_permission(request, obj):
            raise PermissionDenied

        readonly = False
        if extra_context:
            readonly = extra_context.get("readonly", False)
        request.help_key = '{}.add_{}'.format(self.model._meta.app_label, self.model.__name__.lower())
        if not readonly:
            more_context = dict(title='Editar %s' % str(obj))
        else:
            more_context = dict(title='Visualizar %s' % str(obj))
        utils.breadcrumbs_add(request, more_context)
        more_context.update(extra_context or {})
        return super().change_view(request, object_id, form_url, more_context)

    @csrf_protect_m
    @transaction.atomic
    def delete_view(self, request, object_id, extra_context=None):
        extra_context = dict(title='Remover %s' % self.model._meta.verbose_name)
        utils.breadcrumbs_add(request, extra_context)
        if request.POST:
            password = request.POST.get('password', None)
            if not password:
                return httprr('.', 'Preencha sua senha para confirmar a remoção.', 'error')
            elif not authenticate(username=request.user.username, password=password):
                return httprr('.', 'Senha incorreta.', 'error')
        return super().delete_view(request, object_id, extra_context)

    def response_delete(self, request, obj_display, obj_id):
        """
        Determine the HttpResponse for the delete_view stage.
        """
        opts = self.model._meta
        msg = f'{opts.verbose_name} "{obj_display}": excluído com sucesso.'

        self.message_user(
            request,
            msg,
            messages.SUCCESS,
        )

        if self.has_change_permission(request, None):
            post_url = reverse(
                'admin:{}_{}_changelist'.format(opts.app_label, opts.model_name),
                current_app=self.admin_site.name,
            )
            preserved_filters = self.get_preserved_filters(request)
            post_url = add_preserved_filters(
                {'preserved_filters': preserved_filters, 'opts': opts}, post_url
            )
        else:
            post_url = reverse('admin:index', current_app=self.admin_site.name)
        return HttpResponseRedirect(post_url)

    def response_change(self, request, obj):
        if "_continue" in request.POST or "_addanother" in request.POST:
            return super().response_change(request, obj)
        elif "fancybox" in request.GET or "_popup" in request.POST:
            self.message_user(request, 'Atualização realizada com sucesso.')
            return HttpResponse('<script>parent.close_fancybox();</script>')
        else:
            self.message_user(request, 'Atualização realizada com sucesso.')
            return HttpResponseRedirect(utils.breadcrumbs_previous_url(request))

    def response_add(self, request, obj, post_url_continue=None):
        msg = 'Cadastro realizado com sucesso.'
        if hasattr(obj, 'get_absolute_url'):
            msg = mark_safe(msg + f' <a href="{obj.get_absolute_url()}">Acesse o cadastro</a>.')

        if "_continue" in request.POST or "_addanother" in request.POST:
            return super().response_change(request, obj)
        elif "fancybox" in request.GET or "_popup" in request.POST:
            self.message_user(request, msg)
            return HttpResponse('<script>parent.close_fancybox();</script>')
        else:
            self.message_user(request, msg)
            return HttpResponseRedirect(utils.breadcrumbs_previous_url(request))

    def get_urls(self):
        new_urls = [path('<str:obj_pk>/view/', self.render_view_object)]

        return new_urls + super().get_urls()

    def get_view_obj_items(self, obj, safe=None):
        is_safe = safe

        def _get_fieldsets(self):
            if self.fieldsets:
                return self.fieldsets
            else:
                fields = [f.name for f in obj.__class__._meta.fields if f.name != 'id']
                return (('', {'fields': (fields,)}),)

        fieldsets = _get_fieldsets(self)
        max_fields_by_row = 1
        for fieldset_name, fieldset_dict in fieldsets:
            for item in fieldset_dict['fields']:
                if isinstance(item, str):
                    continue
                if len(item) > max_fields_by_row:
                    max_fields_by_row = len(item)

        items = []
        for fieldset_name, fieldset_dict in fieldsets:
            item_dict = dict(fieldset=fieldset_name, rows=[])
            for fieldset_fields_item in fieldset_dict['fields']:
                if isinstance(fieldset_fields_item, str):
                    fieldset_fields_item = [fieldset_fields_item]
                fields = []
                for field_name in fieldset_fields_item:
                    last_field_in_row = field_name == fieldset_fields_item[-1]
                    if last_field_in_row:
                        colspan = (max_fields_by_row - len(fieldset_fields_item)) * 2 + 1
                    else:
                        colspan = 1
                    try:
                        model_field = self.model._meta.get_field(field_name)
                        if hasattr(obj, 'get_{}_display'.format(field_name)):
                            valor = getattr(obj, 'get_{}_display'.format(field_name))
                        elif type(model_field) in [ManyToManyField, ManyToManyFieldPlus]:
                            valor = getattr(obj, field_name).all()
                            is_safe = True
                        else:
                            valor = getattr(obj, field_name)
                            is_safe = False

                        field_dict = dict(label=model_field.verbose_name, value=valor, colspan=colspan, is_safe=is_safe)
                        fields.append(field_dict)
                    except Exception:
                        pass
                item_dict['rows'].append(fields)
            items.append(item_dict)
        return items

    def get_action_bar_view(self, request, obj):
        return []

    def _get_first_object(self, request, obj_pk):
        return self.model.objects.filter(pk=int(obj_pk)).first()

    def render_view_object(self, request, obj_pk):
        safe = hasattr(self, 'safe_view') and self.safe_view or False
        obj = self._get_first_object(request, obj_pk)
        if not obj:
            raise Http404
        if not self.has_view_permission(request, obj):
            raise PermissionDenied

        title = str(obj)
        obj_items = self.get_view_obj_items(obj, safe)
        object_tools_items = self.get_action_bar_view(request, obj)

        inlines = dict()
        for func_name in self.get_view_inlines(request):
            func = getattr(self, func_name)
            columns = getattr(func, 'columns', ['__str__'])
            inline_items = []
            items_safe = []
            objects = func(obj)
            if not objects:
                continue
            for model_obj in objects:
                model_cls = model_obj.__class__
                values = []
                for col in columns:
                    values.append(eval_attr(model_obj, col))
                inline_items.append(values)

            columns_verbose_names = []
            for col in columns:
                if col == '__str__':
                    verbose_name = model_cls._meta.verbose_name
                else:
                    verbose_name = model_cls._meta.get_field(col).verbose_name
                columns_verbose_names.append(verbose_name)

            inlines[getattr(func, 'short_description', func_name)] = dict(columns=columns_verbose_names, items=inline_items, items_safe=items_safe)

        return utils.render('djtools/templates/adminutils/render_view_object.html', locals())

    def get_all_tabs(self, request):
        tabs = self.get_tabs(request)

        if self.show_tab_any_data and 'tab_any_data' not in tabs:
            tabs = ['tab_any_data'] + tabs

        return tabs

    def tab_any_data(self, request, queryset):
        return queryset

    tab_any_data.short_description = 'Todos'

    def get_object(self, request, object_id, from_field=None):
        # No SUAP só é utilizado id inteiro
        try:
            int(object_id)
        except Exception:
            return None
        return super().get_object(request, object_id, from_field)


class CompareVersionAdminPlus(CompareVersionAdmin):
    def compare(self, obj, version1, version2):
        diff, has_unfollowed_fields = super().compare(obj, version1, version2)
        if hasattr(self, 'list_display_compare'):
            displayed_diff = []
            for diff_field in diff:
                if diff_field['field'].name in self.list_display_compare:
                    displayed_diff.append(diff_field)

            diff = displayed_diff
        return diff, has_unfollowed_fields


class ReadOnlyAdmin(ModelAdminPlus):
    """
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_readonly_inlines = dict()

    def get_readonly_fields(self, request, obj=None):
        if self.user_is_readonly(request):
            return list(self.readonly_fields) + [field.name for field in obj._meta.fields]
        return super(ModelAdminPlus, self).get_readonly_fields(request, obj)

    def has_add_permission(self, request, obj=None):
        if not self.user_is_readonly(request):
            return super().has_add_permission(request)
        return False

    def has_delete_permission(self, request, obj=None):
        if not self.user_is_readonly(request):
            return super().has_delete_permission(request)
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if self.user_is_readonly(request):
            if 'delete_selected' in actions:
                del actions['delete_selected']
        return actions

    def change_view(self, request, object_id, extra_context=None):

        extra_context = extra_context or {}
        if not request.user.is_superuser and self.user_is_readonly(request):
            request.readonly = True
            extra_context.update(
                {
                    # set a context var telling our customized template to suppress the Save button group
                    'readonly': True
                }
            )
        try:
            return super().change_view(request, object_id, extra_context=extra_context)
        except PermissionDenied:
            pass
        #
        if request.method == 'POST':
            raise PermissionDenied
        #
        return super().change_view(request, object_id, extra_context=extra_context)

    def view_object_icon(self, obj):
        """
        Templatetag para incluir ícone de remoção do obj, já testando se o usuário
        autenticado tem permissões para isso.
        """
        from djtools.utils import get_admin_object_url

        out = []
        icons_html = [mark_safe(icon('view', get_admin_object_url(obj), 'Ver {}'.formatunicode(obj)))]
        for icon_html in icons_html:
            if icon_html:
                out.append(icon_html)
        return ''.join(out)

    def show_list_display_icons(self, obj):
        if self.user_is_readonly(self.request):
            return self.view_object_icon(obj)
        else:
            return super().show_list_display_icons(obj)

    show_list_display_icons.allow_tags = True
    show_list_display_icons.short_description = '#'

    def user_is_readonly(self, request):
        groups = [x.name for x in request.user.groups.all()]
        return "readonly" in groups


class NonrelatedInlineModelAdminChecks(InlineModelAdminChecks):
    """
    Check used by the admin system to determine whether or not an inline model
    has a relationship to the parent object.
    In this case we always want this check to pass.
    """

    def _check_exclude_of_parent_model(self, obj, parent_model):
        return []

    def _check_relation(self, obj, parent_model):
        return []


class NonrelatedStackedInline(admin.StackedInline):
    """
    Stacked inline base class for models not explicitly related to the inline
    model.
    """
    checks_class = NonrelatedInlineModelAdminChecks
    formset = NonrelatedInlineFormSet

    def get_form_queryset(self, obj):
        raise NotImplementedError()

    def save_new_instance(self, parent, instance):
        raise NotImplementedError()

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            self.update_instance(formset.instance, instance)
            instance.save()
        formset.save_m2m()

    def get_formset(self, request, obj=None, **kwargs):
        if 'fields' in kwargs:
            fields = kwargs.pop('fields')
        else:
            fields = flatten_fieldsets(self.get_fieldsets(request, obj))

        exclude = [*(self.exclude or []), *self.get_readonly_fields(request, obj)]
        if self.exclude is None and hasattr(self.form, '_meta') and self.form._meta.exclude:
            exclude.extend(self.form._meta.exclude)
        exclude = exclude or None

        can_delete = self.can_delete and self.has_delete_permission(request, obj)

        queryset = self.model.objects.none()
        if obj:
            queryset = self.get_form_queryset(obj)

        defaults = {
            'form': self.form,
            'formfield_callback': partial(self.formfield_for_dbfield, request=request),
            'formset': self.formset,
            'extra': self.get_extra(request, obj),
            'can_delete': can_delete,
            'can_order': False,
            'fields': fields,
            'min_num': self.get_min_num(request, obj),
            'max_num': self.get_max_num(request, obj),
            'exclude': exclude,
            'queryset': queryset,
            **kwargs,
        }

        if defaults['fields'] is None and not modelform_defines_fields(defaults['form']):
            defaults['fields'] = ALL_FIELDS

        return nonrelated_inlineformset_factory(self.model, save_new_instance=self.save_new_instance, **defaults)


class ReverseInlineFormSet(BaseModelFormSet):
    '''
    A formset with either a single object or a single empty
    form. Since the formset is used to render a required OneToOne
    relation, the forms must not be empty.
    '''
    parent_fk_name = ''

    def __init__(self, data=None, files=None, instance=None, prefix=None, queryset=None, save_as_new=False):
        object = getattr(instance, self.parent_fk_name, None)
        #
        if object:
            qs = self.model.objects.filter(pk=object.pk)
        else:
            qs = self.model.objects.none()
            self.extra = 1
        #
        super().__init__(data, files, prefix=prefix, queryset=qs)
        for form in self.forms:
            form.empty_permitted = False


def _get_parent_fk_field(obj, formset):
    return next((f for f in obj._meta.fields if f.name == formset.parent_fk_name), None)


def _remove_blank_reverse_inlines(obj, formset_inline_tuples):
    """
    Hacky implementation, but for some reasons blank inlines are being treated
    as invalid. So, let's remove them from validation, since we know that they are
    actually valid.
    """
    def to_filter(formset):
        if not isinstance(formset, ReverseInlineFormSet):
            return True
        field = _get_parent_fk_field(obj, formset)
        return not (field.blank and not formset.has_changed())
    return [a for a in filter(lambda t: to_filter(t[0]), formset_inline_tuples)]


def reverse_inlineformset_factory(model, parent_fk_name, form=ModelFormPlus, fields=None, exclude=None, formfield_callback=lambda f: f.formfield()):
    if fields is None and exclude is None:
        related_fields = [f for f in model._meta.get_fields() if (f.one_to_many or f.one_to_one or f.many_to_many) and f.auto_created and not f.concrete]
        fields = [f.name for f in model._meta.get_fields() if f not in related_fields]  # ignoring reverse relations
    #
    kwargs = {
        'form': form,
        'formfield_callback': formfield_callback,
        'formset': ReverseInlineFormSet,
        'extra': 0,
        'can_delete': True,
        'can_order': False,
        'fields': fields,
        'exclude': exclude,
        'max_num': 1,
    }
    FormSet = modelformset_factory(model, **kwargs)
    FormSet.parent_fk_name = parent_fk_name
    return FormSet


class ReverseInlineModelAdmin(InlineModelAdmin):
    '''
    Use the name and the help_text of the owning models field to
    render the verbose_name and verbose_name_plural texts.
    '''

    def __init__(self, parent_model, parent_fk_name, model, admin_site, inline_type):
        self.template = 'admin/edit_inline/%s.html' % inline_type
        self.parent_fk_name = parent_fk_name
        self.model = model
        field_descriptor = getattr(parent_model, self.parent_fk_name)
        field = field_descriptor.field
        #
        self.verbose_name_plural = field.verbose_name.title()
        self.verbose_name = field.help_text
        if not self.verbose_name:
            self.verbose_name = self.verbose_name_plural
        #
        super().__init__(parent_model, admin_site)

    def get_formset(self, request, obj=None, **kwargs):

        if 'fields' in kwargs:
            fields = kwargs.pop('fields')
        elif self.get_fieldsets(request, obj):
            fields = flatten_fieldsets(self.get_fieldsets(request, obj))
        else:
            fields = None

        # want to combine exclude arguments - can't do that if they're None
        # also, exclude starts as a tuple - need to make it a list
        non_editable_fields = [f for f in self.model._meta.fields if not f.editable]
        exclude = list(kwargs.get("exclude", []))
        exclude.extend(self.get_readonly_fields(request, obj))
        exclude_2 = self.exclude or []
        exclude.extend(list(exclude_2))
        exclude.extend(non_editable_fields)
        # but need exclude to be None if result is an empty list
        exclude = exclude or None

        defaults = {
            "form": self.form,
            "fields": fields,
            "exclude": exclude,
            "formfield_callback": partial(self.formfield_for_dbfield, request=request),
        }
        kwargs.update(defaults)
        return reverse_inlineformset_factory(self.model, self.parent_fk_name, **kwargs)


class ReverseModelAdminPlus(ModelAdminPlus):
    '''
    Patched ModelAdmin class. The add_view method is overridden to
    allow the reverse inline formsets to be saved before the parent
    model.
    '''

    def __init__(self, model, admin_site):
        #
        super().__init__(model, admin_site)
        self.exclude = list(self.exclude or [])
        inline_instances = []
        for field_name in self.inline_reverse:
            #
            kwargs = {}
            admin_class = None
            #
            if isinstance(field_name, tuple):
                kwargs = field_name[1]
                field_name = field_name[0]
            elif isinstance(field_name, dict):
                kwargs = field_name.get('kwargs', kwargs)
                admin_class = field_name.get('admin_class', admin_class)
                field_name = field_name['field_name']
            #
            field = model._meta.get_field(field_name)
            if isinstance(field, (models.OneToOneField, models.ForeignKey)):
                if admin_class:
                    admin_class_to_use = type(
                        str('DynamicReverseInlineModelAdmin_{}'.format(admin_class.__name__)),
                        (admin_class, ReverseInlineModelAdmin),
                        {},
                    )
                else:
                    admin_class_to_use = ReverseInlineModelAdmin
                #
                name = field.name
                parent = field.remote_field.model
                inline = admin_class_to_use(model, name, parent, admin_site, self.inline_type)
                if kwargs:
                    inline.__dict__.update(kwargs)
                inline_instances.append(inline)
                self.exclude.append(name)
        # These are the inline reverse instances for ReverseModelAdmin
        self.tmp_inline_instances = inline_instances

    def get_inline_instances(self, request, obj=None):
        own = list(filter(
            lambda inline: inline.has_view_or_change_permission(request, obj) or
            inline.has_add_permission(request, obj) or
            inline.has_delete_permission(request, obj), self.tmp_inline_instances)
        )
        return own + super().get_inline_instances(request, obj)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        return self._changeform_view(request, object_id, form_url, extra_context)

    def add_view(self, request, form_url='', extra_context=None):
        return self._changeform_view(request, None, form_url, extra_context)

    def _save_object(self, request, new_object, form, formsets, add):
        self.save_model(request, new_object, form, change=not add)
        self.save_related(request, form, formsets, change=not add)
        form.save_m2m()
        change_message = self.construct_change_message(request, form, formsets, add)
        if add:
            self.log_addition(request, new_object, change_message)
        else:
            self.log_change(request, new_object, change_message)

    def _changeform_view(self, request, object_id, form_url, extra_context):
        add = object_id is None
        #
        model = self.model
        opts = model._meta
        #
        if add:
            if not self.has_add_permission(request):
                raise PermissionDenied
            obj = None

        else:
            obj = self.get_object(request, unquote(object_id))

            if request.method == 'POST':
                if not self.has_change_permission(request, obj):
                    raise PermissionDenied
            else:
                if not self.has_view_or_change_permission(request, obj):
                    raise PermissionDenied

            if obj is None:
                return self._get_obj_does_not_exist_redirect(request, opts, object_id)

        formsets = []
        model_form = self.get_form(request, obj=obj, change=not add)
        if request.method == 'POST':
            form = model_form(request.POST, request.FILES, instance=obj)
            form_validated = form.is_valid()
            #
            if form_validated:
                new_object = self.save_form(request, form, change=not add)
            else:
                new_object = form.instance
            formsets, inline_instances = self._create_formsets(request, new_object, change=not add)
            formset_inline_tuples = zip(formsets, self.get_inline_instances(request))
            formset_inline_tuples = _remove_blank_reverse_inlines(new_object, formset_inline_tuples)
            formsets = [t[0] for t in formset_inline_tuples]
            #
            if form_validated and not formsets:
                self._save_object(request, new_object, form, formsets, add)
                return self.response_add(request, new_object)
            elif form_validated and all_valid(formsets):
                # Here is the modified code.
                for formset, inline in formset_inline_tuples:
                    if not isinstance(inline, ReverseInlineModelAdmin):
                        continue
                    # The idea or this piece is coming from:
                    #  https://stackoverflow.com/questions/50910152/inline-formset-returns-empty-list-on-save.
                    # Without this, formset.save() was returning None for forms that
                    # haven't been modified
                    forms = [f for f in formset]
                    if not forms:
                        continue
                    obj = forms[0].save()
                    setattr(new_object, inline.parent_fk_name, obj)
                #
                self._save_object(request, new_object, form, formsets, add)
                for formset in formsets:
                    self.save_formset(request, form, formset, change=not add)

                # self.log_addition(request, new_object)
                return self.response_add(request, new_object)
        else:
            # Prepare the dict of initial data from the request.
            # We have to special-case M2Ms as a list of comma-separated PKs.
            initial = dict(request.GET.items())
            for k in initial:
                try:
                    f = opts.get_field(k)
                except FieldDoesNotExist:
                    continue
                if isinstance(f, models.ManyToManyField):
                    initial[k] = initial[k].split(",")
            if add:
                form = model_form(initial=initial)
                prefixes = {}
                for FormSet, inline in self.get_formsets_with_inlines(request):
                    prefix = FormSet.get_default_prefix()
                    prefixes[prefix] = prefixes.get(prefix, 0) + 1

                    if prefixes[prefix] != 1:
                        prefix = "{}-{}".format(prefix, prefixes[prefix])
                    #
                    formset = FormSet(instance=self.model(), prefix=prefix)
                    formsets.append(formset)
            else:
                form = model_form(instance=obj)
                formsets, inline_instances = self._create_formsets(request, obj, change=True)

        if not add and not self.has_change_permission(request, obj):
            readonly_fields = flatten_fieldsets(
                self.get_fieldsets(request, obj))
        else:
            readonly_fields = self.get_readonly_fields(request, obj)

        adminForm = helpers.AdminForm(
            form, list(self.get_fieldsets(request)),
            self.prepopulated_fields,
            readonly_fields=readonly_fields,
            model_admin=self
        )
        media = self.media + adminForm.media
        inline_admin_formsets = self.get_inline_formsets(request, formsets, self.get_inline_instances(request), obj)

        for inline_formset in inline_admin_formsets:
            media = media + inline_formset.media

        # Inherit the default context from admin_site
        context = self.admin_site.each_context(request)
        reverse_admin_context = {
            'title': _(('Change %s', 'Add %s')[add]) % force_str(opts.verbose_name),
            'adminform': adminForm,
            'is_popup': False,
            'object_id': object_id,
            'original': obj,
            'media': mark_safe(media),
            'inline_admin_formsets': inline_admin_formsets,
            'errors': helpers.AdminErrorList(form, formsets),
            'app_label': opts.app_label,
        }
        context.update(reverse_admin_context)
        context.update(extra_context or {})
        return self.render_change_form(request, context, form_url=form_url, add=add, change=not add, obj=obj)
