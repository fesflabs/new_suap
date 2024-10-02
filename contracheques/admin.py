from django.contrib import admin, messages
from django.utils.safestring import mark_safe

from djtools.choices import Meses
from contracheques.forms import FormRubrica, AgrupamentoRubricasForm
from contracheques.models import Rubrica, ContraCheque, Beneficiario, AgrupamentoRubricas
from djtools.contrib.admin import ModelAdminPlus


###############
# Rubrica
###############
from djtools.templatetags.tags import icon


class RubricaAdmin(ModelAdminPlus):
    list_display = ("codigo", "nome", "excluido")
    list_filter = ("excluido",)
    search_fields = ("nome", "codigo")
    ordering = ("excluido", "nome", "codigo")

    def get_action_bar(self, request):
        items = super().get_action_bar(request)
        return items

    form = FormRubrica


admin.site.register(Rubrica, RubricaAdmin)


###############
# Contra-Cheque
###############


class ContraChequeAdmin(ModelAdminPlus):
    list_display = (
        "get_info_servidor_ou_pensionista",
        "servidor_situacao",
        "get_mes",
        "ano",
        "tipo_importacao",
        "excluido",
    )
    list_display_icons = True
    list_filter = ("ano", "mes", "servidor_situacao", "tipo_importacao", "excluido")
    ordering = ("servidor", "ano", "mes")
    search_fields = ("servidor__nome", "servidor__matricula", "pensionista__nome")
    actions = ("excluir_selecionados",)

    def excluir_selecionados(self, request, queryset):
        ids = request.POST.getlist("_selected_action")
        if ids:
            ids = list(map(int, ids))
        qs = queryset.filter(id__in=ids)
        if qs.exists():
            for cc in qs:
                cc.excluido = True
                cc.save()
            messages.success(request, "Contracheques excluuídos com sucesso.")

    excluir_selecionados.short_description = "Excluir selecionados?"

    def get_action_bar(self, request):
        items = super().get_action_bar(request)
        if request.user.is_superuser:
            items.append(dict(url="importar_do_arquivo/", label="Importar do arquivo"))
        return items

    def get_info_servidor_ou_pensionista(self, obj):
        if obj.pensionista:
            return mark_safe(obj.pensionista.nome)
        return mark_safe("{} ({})".format(obj.servidor.nome, obj.servidor.matricula))

    get_info_servidor_ou_pensionista.short_description = "Nome"

    def icone_detalhar(self, obj):
        return mark_safe(icon("view", "/contracheques/contra_cheque/{}".format(obj.pk)))

    icone_detalhar.short_description = ""

    def get_mes(self, obj):
        return mark_safe(Meses.get_mes(obj.mes))

    get_mes.short_description = "Mês"


admin.site.register(ContraCheque, ContraChequeAdmin)


###############
# Beneficiarios
###############


class BeneficiarioAdmin(ModelAdminPlus):
    pass


admin.site.register(Beneficiario, BeneficiarioAdmin)


class AgrupamentoRubricasAdmin(ModelAdminPlus):
    list_display = ("descricao",)
    search_fields = ("descricao", "rubricas__nome", "rubricas__codigo")
    ordering = ("descricao",)

    form = AgrupamentoRubricasForm


admin.site.register(AgrupamentoRubricas, AgrupamentoRubricasAdmin)
