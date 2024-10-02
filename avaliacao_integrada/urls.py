# -*- coding: utf-8 -*
from django.urls import path

from avaliacao_integrada import views

urlpatterns = [
    path('indicador/<int:pk>/', views.indicador),
    path('replicar_indicador/<int:pk>/', views.replicar_indicador),
    path('avaliacao/<int:pk>/', views.avaliacao),
    path('questionario/<int:pk>/', views.questionario),
    path('avaliacao_externa/', views.avaliacao_externa),
    path('avaliacao_externa/<str:token>/<int:segmento>/', views.questionario_avaliacao_externa),
    # Relatórios
    path('relatorio/<int:pk>/<int:pk_avaliacao>/', views.exibir_relatorio_indicador),
    path('relatorio/', views.relatorio),
    path('relatorio_xlsx/', views.relatorio_xlsx),
]
