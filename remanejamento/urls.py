# -*- coding: utf-8 -*
from django.urls import path

from remanejamento import views

urlpatterns = [
    path('visualizar_recurso_edital/<int:recurso_pk>/', views.visualizar_recurso_edital),
    path('recurso_edital/<int:edital_pk>/', views.recurso_edital),
    path('inscrever/<int:edital_pk>/', views.inscrever),
    path('inscricao/<int:inscricao_pk>/', views.inscricao),
    path('inscricao/<int:inscricao_pk>/desistir/', views.inscricao_desistir),
    path('inscricao/<int:inscricao_pk>/imprimir/', views.inscricao_imprimir),
    path('inscricao/<int:inscricao_pk>/excluir_recurso/', views.inscricao_excluir_recurso),
    path('inscricoes_csv/<int:edital_pk>/', views.inscricoes_csv),
    path('adicionar_disciplinas/<int:edital_pk>/', views.adicionar_disciplinas),
    path('inscricao_nao_habilitada/<int:inscricao_pk>/', views.inscricao_nao_habilitada),
    path('adicionar_disciplina_itens/<int:edital_pk>/', views.adicionar_disciplina_itens),
]
