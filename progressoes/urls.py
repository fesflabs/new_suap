# -*- coding: utf-8 -*
from django.urls import path

from progressoes import views

urlpatterns = [
    path('avaliacao_modelo_visualizar/<int:avaliacao_modelo_id>/', views.avaliacao_modelo_visualizar),
    path('editar_processo/<int:processo_id>/', views.editar_processo),
    path('detalhes_processo/<int:processo_id>/', views.detalhes_processo),
    path('adicionar_periodo/<int:processo_id>/', views.adicionar_periodo),
    path('adicionar_avaliadores/<int:periodo_id>/', views.adicionar_avaliadores),
    path('editar_periodo/<int:periodo_id>/', views.editar_periodo),
    path('remover_periodo/<int:periodo_id>/', views.remover_periodo),
    path('liberar_avaliacoes/<int:processo_id>/', views.liberar_avaliacoes),
    path('abrir_avaliacao/<str:avaliacao_id>/', views.abrir_avaliacao),
    path('meus_processos/', views.meus_processos),
    path('minhas_avaliacoes/', views.minhas_avaliacoes),
    path('reavaliar_avaliacao/<str:avaliacao_id>/', views.reavaliar_avaliacao),
    path('finalizar_processo/<int:processo_id>/', views.finalizar_processo),
    path('reabrir_processo/<int:processo_id>/', views.reabrir_processo),
    path('cancelar_tramite/<int:processo_id>/', views.cancelar_tramite),
    path('imprimir_processo/<int:processo_id>/', views.imprimir_processo),
    path('assinar_avaliacao/<str:avaliacao_id>/', views.assinar_avaliacao),
    path('assinar_processo/<str:processo_id>/', views.assinar_processo),
    path('recalcular_medias/<int:processo_id>/', views.recalcular_medias),
    path('gerar_protocolo_processo_eletronico/<int:processo_id>/', views.gerar_protocolo_processo_eletronico),
    path('selecionar_protocolo_processo_eletronico/<int:processo_id>/', views.selecionar_protocolo_processo_eletronico),
]
