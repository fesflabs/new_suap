# -*- coding: utf-8 -*-
import time
from django.contrib import admin
from django.utils.safestring import mark_safe
from djtools.contrib.admin import ModelAdminPlus, NonrelatedStackedInline
from django.urls import reverse
from comum.models import User
from .models import LdapConf, LdapGroup, LdapUser
from .forms import LdapGroupForm
from .utils import extract_cn_from_ldap_user


class LdapUserStackedInline(NonrelatedStackedInline):
    model = LdapUser
    extra = 0
    can_delete = False

    def get_form_queryset(self, obj):
        return self.model.objects.filter(member_of=obj.dn)

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class LdapConfAdmin(ModelAdminPlus):
    ordering = ('-active', 'priority', )
    list_display = ['uri', 'active', 'get_status', 'get_opcoes', 'get_latencia', 'priority']

    def get_status(self, obj):
        if obj.active:
            try:
                obj.bind()
                retorno = '<span class="status status-success">Conectividade OK</span>'
            except Exception as e:
                retorno = '<span class="status status-error">Falha na conectividade: %s</span>' % e
        else:
            retorno = '<span class="status status-alert">Ldap Inativo</span>'
        return mark_safe(retorno)

    get_status.short_description = 'Status'

    def get_latencia(self, obj):
        if obj.active:
            valor_inicial = time.time()
            try:
                username = User.objects.latest('id').username
                filterstr = '{0}{1}'.format(obj.filterstr_prefix, username)
                obj.search_objects(filterstr=filterstr)
            except Exception:
                pass
            valor = time.time() - valor_inicial
            return '{0}ms'.format(valor * 1000)
        else:
            return 'Não se aplica.'

    get_latencia.short_description = 'Latência'

    def get_opcoes(self, obj):
        return mark_safe(
            """
        <ul>
            <li><a href="/ldap_backend/search/%(pk)d/">Buscar usuário</a></li>
        </ul>
        """
            % dict(pk=obj.pk)
        )

    get_opcoes.short_description = 'Opções'


admin.site.register(LdapConf, LdapConfAdmin)


class LDAPUserAdmin(ModelAdminPlus):
    #
    list_display_icons = True
    show_tab_any_data = False
    list_per_page = 10
    #
    exclude = ['dn', 'objectClass']
    list_display = ['sAMAccountName', 'name', 'mail']
    search_fields = ['sAMAccountName', 'name', 'mail']

    def _get_first_object(self, request, obj_pk):
        return self.model.objects.filter(pk=obj_pk).first()

    def get_object(self, request, object_id, from_field=None):
        return super(ModelAdminPlus, self).get_object(request, object_id, from_field)

    def get_queryset(self, request, manager=None, *args, **kwargs):
        username = self.request.user.username
        qs = LdapUser.objects.filter(sAMAccountName=username)
        return qs

    def get_search_results(self, request, queryset, search_term):
        if search_term:
            queryset = LdapUser.objects.all()
        return super().get_search_results(request, queryset, search_term)


admin.site.register(LdapUser, LDAPUserAdmin)


class LDAPGroupAdmin(ModelAdminPlus):
    list_display = ['cn', 'display_members', 'get_options']
    search_fields = ['cn']
    list_display_icons = False
    list_per_page = 20
    change_form = LdapGroupForm
    inlines = [
        LdapUserStackedInline
    ]
    readonly_fields = ['cn', 'sAMAccountName', 'dn', 'name']

    def _get_first_object(self, request, obj_pk):
        return self.model.objects.filter(pk=obj_pk).first()

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_object(self, request, object_id, from_field=None):
        return super(ModelAdminPlus, self).get_object(request, object_id, from_field)

    def get_options(self, obj):
        html = '<ul class="action-bar">'
        html += '<li><a class="btn success" href="{0}">Gerenciar Grupo</a></li>'.format(reverse('ldap-group-change', args=[obj.cn]))
        html += '</ul>'

        return mark_safe(html)
    #
    get_options.short_description = 'Ações'

    def display_members(self, obj):
        members_cn = []
        for member in obj.member:
            member_cn = extract_cn_from_ldap_user(member)
            members_cn.append(member_cn)
        return members_cn

    display_members.short_description = 'Members'


admin.site.register(LdapGroup, LDAPGroupAdmin)
