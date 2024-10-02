# -*- coding: utf-8 -*-

from django.contrib import admin
from django.utils.safestring import mark_safe

from djtools.contrib.admin import ModelAdminPlus
from microsoft.models import ConfiguracaoAcessoDreamspark
from microsoft.forms import ConfiguracaoAcessoDreamsparkForm


class ConfiguracaoAcessoDreamsparkAdmin(ModelAdminPlus):
    list_display = ['descricao', 'tipo', 'get_cursos']
    form = ConfiguracaoAcessoDreamsparkForm

    def get_cursos(self, obj):
        out = '<ul>'
        for curso in obj.cursos.all():
            out += '<li>%s</li>' % str(curso)
        out += '<ul>'
        return mark_safe(out)

    get_cursos.short_description = 'Cursos'
    get_cursos.attrs = {'width': '18px'}


admin.site.register(ConfiguracaoAcessoDreamspark, ConfiguracaoAcessoDreamsparkAdmin)
