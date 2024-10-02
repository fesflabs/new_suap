# -*- coding: utf-8 -*

from django.urls import path

from encceja import views

urlpatterns = [
    path('solicitacao/<int:pk>/', views.solicitacao),
    path('importar_resultado/', views.importar_resultado),
    path('quantitativo/', views.quantitativo),
    path('cancelar_solicitacao/<int:pk>/', views.cancelar_solicitacao),
]
