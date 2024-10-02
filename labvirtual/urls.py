from django.urls import path
from .views import sync_desktop_pools_view, desktop_pool_detail_view
from .views import (
    # Solicitacao e agendamento
    solicitacao_agendamento_create_view, solicitacao_agendamento_detail_view,
    deferir_solicitacao_agendamento_view, indeferir_solicitacao_agendamento_view,
    cancelar_solicitacao_agendamento_view,
    agendamento_sync_view, agendamento_shutdown_view,
    procurar_usuario_view, adicionar_membro_view, remover_membro_view,
    agendamento_labvirtual_detail_view
)
app_name = "labvirtual"

urlpatterns = [
    # Desktop Pools
    path("labvirtual/sync_desktop_pools/", view=sync_desktop_pools_view, name="sync_desktop_pools"),
    path("labvirtual/<int:pk>/", view=desktop_pool_detail_view, name="desktop_pool_detail"),

    # Solicitação
    path("solicitar_agendamento/<int:pk>", view=solicitacao_agendamento_create_view, name="solicitar_agendamento"),
    path("solicitar_agendamento/diario/<int:pk>", view=solicitacao_agendamento_create_view, name="solicitar_agendamento"),
    path("solicitacao_agendamento/<int:pk>", view=solicitacao_agendamento_detail_view, name="solicitacao_agendamento"),
    path("solicitacao_agendamento/deferir/<int:pk>", view=deferir_solicitacao_agendamento_view, name="deferir_solicitacao"),
    path("solicitacao_agendamento/indeferir/<int:pk>", view=indeferir_solicitacao_agendamento_view, name="indeferir_solicitacao"),
    path("solicitacao_agendamento/cancelar/<int:pk>", view=cancelar_solicitacao_agendamento_view, name="cancelar_solicitacao"),

    # Agendamento
    path("agendamento/laboratoriovirtual/<int:pk>/", view=agendamento_labvirtual_detail_view, name="agendamento_labvirtual"),
    path("agendamento/sync/<int:pk>/", view=agendamento_sync_view, name="liberar_agendamento"),
    path("agendamento/shutdown/<int:pk>/", view=agendamento_shutdown_view, name="encerrar_agendamento"),

    # Gerenciamento dos grupos
    path("solicicao_agendamento/procurar_usuario/<int:pk>", procurar_usuario_view, name='procurar_usuario'),
    path('solicitacao_agendamento/adicionar_membro/<int:pk>/<int:uid>', adicionar_membro_view, name='adicionar_membro'),
    path('solicitacao_agendamento/remover_member/<int:pk>/<int:uid>', remover_membro_view, name='remover_membro')


]
