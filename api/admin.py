# -*- coding: utf-8 -*-
from djtools.contrib.admin import ModelAdminPlus
from django.contrib import admin


class AplicacaoOAuth2Admin(ModelAdminPlus):
    list_display = ('id', 'name', 'user', 'client_type', 'authorization_grant_type')
    list_filter = ('client_type', 'authorization_grant_type', 'skip_authorization', 'user')
    radio_fields = {
        'client_type': admin.HORIZONTAL,
        'authorization_grant_type': admin.VERTICAL,
    }
