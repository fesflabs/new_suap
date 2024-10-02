# -*- coding: utf-8 -*-
from django.contrib.admin.filters import SimpleListFilter
from django.db.models.aggregates import Max
from django.forms.utils import flatatt
from django.forms.widgets import TextInput
from django.utils.encoding import force_str
from django.utils.html import format_html

from comum.models import User

from djtools.forms.fields import CharFieldPlus
from djtools.templatetags.filters import in_group
from edu.models import SituacaoMatriculaPeriodo
from edu.models.cadastros_gerais import SituacaoMatricula


class SituacaoUltimaMatriculaPeriodoFilter(SimpleListFilter):
    title = 'Situação da Matrícula Período'
    parameter_name = 'situacao_ultima_matricula_periodo'

    def lookups(self, request, model_admin):
        return ((x.pk, x.descricao) for x in SituacaoMatriculaPeriodo.objects.all())

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                aluno__matriculaperiodo__pk__in=queryset.annotate(max_matricula_periodo=Max('aluno__matriculaperiodo__id')).values_list('max_matricula_periodo', flat=True),
                aluno__matriculaperiodo__situacao__pk=self.value(),
            ).distinct()


class SituacaoUltimaMatriculaPeriodoAprendizagemFilter(SimpleListFilter):
    title = 'Situação da Matrícula Período'
    parameter_name = 'situacao_ultima_matricula_periodo'

    def lookups(self, request, model_admin):
        return ((x.pk, x.descricao) for x in SituacaoMatriculaPeriodo.objects.all())

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                aprendiz__matriculaperiodo__pk__in=queryset.annotate(max_matricula_periodo=Max('aprendiz__matriculaperiodo__id')).values_list('max_matricula_periodo', flat=True),
                aprendiz__matriculaperiodo__situacao__pk=self.value(),
            ).distinct()


class TipoAditivoContratualFilter(SimpleListFilter):
    title = 'Tipo de Aditivo Contratual'
    parameter_name = 'tipo_aditivo_contratual'

    def lookups(self, request, model_admin):
        from estagios.models import TipoAditivo

        return ((x.pk, x.descricao) for x in TipoAditivo.objects.all())

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(estagioaditivocontratual__tipos_aditivo__pk=self.value()).distinct()
        else:
            return queryset


class PossuiAditivoContratualFilter(SimpleListFilter):
    title = 'Possui Aditivo Contratual?'
    parameter_name = 'possui_aditivo_contratual'

    def lookups(self, request, model_admin):
        return ((1, 'Sim'), (2, 'Não'))

    def queryset(self, request, queryset):
        if self.value():
            if int(self.value()) == 1:
                queryset = queryset.filter(estagioaditivocontratual__pk__gt=0).distinct()
            elif int(self.value()) == 2:
                queryset = queryset.exclude(estagioaditivocontratual__pk__gt=0).distinct()
            return queryset


class ListCharFieldWidget(TextInput):
    def render(self, name, value, attrs=None, rendered=None):
        if value is None:
            value = ['']
        elif not isinstance(value, (list, tuple)):
            value = [value]
        final_attrs = self.build_attrs(attrs)
        #
        tag_input_vazia = format_html('<input{} name={} size=100px />', flatatt(final_attrs), name)
        tag_remove = '<img ' 'src="/static/admin/img/icon-deletelink.svg" ' 'class="cleanValue" ' 'onclick="listcharfield_remove_item(this);">'
        #
        htmls = ['<ul style="padding: 0px 0px 5px 20px;">']
        for value_item in value:
            htmls.append('<li>')
            if value_item != '':
                final_attrs['value'] = force_str(self.format_value(value_item))
                htmls.append(format_html('<input{} name={} size=100px />', flatatt(final_attrs), name))
            else:
                htmls.append(tag_input_vazia)
            htmls.append(tag_remove)
            htmls.append('</li>')
        #
        htmls.append('<li>')
        js_add = '''
            <script type="text/javascript">
                function listcharfield_remove_item(link_remove){{
                    if (confirm('Confirma?') == true){{
                        $(link_remove).prev().remove();
                        $(link_remove).remove();
                    }}
                }}

                function listcharfield_add_item(link_add){{
                    $(link_add).parent().before('<li>{}{}</li>');
                    $(link_add).parent().prev().find("input").focus();
                    return false;
                }}
            </script>
        '''.format(
            tag_input_vazia, tag_remove
        )

        htmls.append('<br><a ' 'href="#" ' 'style="margin-top: 20px; padding-top: 20px;" onclick="listcharfield_add_item(this);">' 'Adicionar novo item' '</a>')
        htmls.append('</li>')
        #
        htmls.append('</ul>')
        #
        html_final = format_html(''.join(htmls)) + js_add
        return html_final

    def value_from_datadict(self, data, files, name):
        return data.getlist(name)


class ListCharField(CharFieldPlus):
    widget = ListCharFieldWidget

    def __init__(self, *args, **kwargs):
        kwargs['width'] = '800'
        super(ListCharField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        if value is None:
            return ['']
        elif not isinstance(value, (list, tuple)):
            return [value]
        return value  # uma lista de unicodes


def get_coordenadores_estagio(aluno):
    return User.objects.filter(groups__name='Coordenador de Estágio', pessoafisica__funcionario__setor__uo=aluno.curso_campus.diretoria.setor.uo)


def get_coordenadores_nomes(coordenadores):
    return ', '.join([coordenador.get_profile().nome for coordenador in coordenadores])


def get_coordenadores_emails(coordenadores):
    return ', '.join([coordenador.email for coordenador in coordenadores])


def get_coordenadores_vinculos(coordenadores):
    vinculos = []
    for coordenador in coordenadores:
        vinculos.append(coordenador.get_vinculo())
    return vinculos


def get_situacoes_irregulares():
    return SituacaoMatricula.objects.exclude(id__in=[SituacaoMatricula.MATRICULADO, SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL])


def visualiza_todos_estagios_afins(user):
    return user.is_superuser or in_group(user, ['Coordenador de Estágio Sistêmico', 'Administrador Acadêmico', 'Auditor', 'Visualizador de Estágios Sistêmico', 'Estagiário Acadêmico Sistêmico'])


def por_extenso(value):
    from comum.utils import extenso

    if bool(value):
        reais, centavos = str(value).split('.')
        return '{}'.format(extenso(reais, centavos))
    else:
        return '-'
