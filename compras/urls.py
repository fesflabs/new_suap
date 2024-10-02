# -*- coding: utf-8 -*

from django.urls import path

from compras import views

urlpatterns = [
    path('processo_compra/<int:pk>/', views.processo_compra),
    path('processo_compra/<int:pk>/validar/', views.processo_compra_validar),
    path('processo_compra_relatorio_ug/<int:pk>/', views.processo_compra_relatorio_ug),
    path('processo_compra_relatorio_campus/<int:pk>/', views.processo_compra_relatorio_campus),
    path('processo_compra_relatorio_geral/<int:pk>/', views.processo_compra_relatorio_geral),
    path('relatorio_processo_compra_campus/<int:pk>/', views.relatorio_processo_compra_campus),
    path('processo_compra_relatorio_cotacao/<int:pk>/', views.processo_compra_relatorio_cotacao),
    path('processo_compra_campus/<int:pk>/', views.processo_compra_campus),
    path('processo_compra_campus/<int:pk>/validar/', views.processo_compra_campus_validar),
    path('processo_compra_editar/<int:pk>/', views.processo_compra_editar),
    path('preencher_materiais_ausentes_campus/<int:pk>/', views.preencher_materiais_ausentes_campus),
    path('detalhar_anexos/<int:pk>/', views.detalhar_anexos),
    path('calendarios_referencia/', views.calendarios_referencia),
    path('calendarios_compra/', views.calendarios_compra),
    path('adicionar_fase/<int:pk>/', views.adicionar_fase),
    path('solicitar_participacao/<int:pk>/', views.solicitar_participacao),

]
