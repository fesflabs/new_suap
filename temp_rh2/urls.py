# -*- coding: utf-8 -*
from django.urls import path

from temp_rh2 import views

urlpatterns = [
    path('competicao_desportiva/inscricao/<int:competicao_pk>/', views.inscricao_competicoes_desportivas),
    path('competicao_desportiva/inscricao/<int:competicao_pk>/<int:inscricao_pk>/', views.inscricao_competicoes_desportivas),
    path('validar/<int:inscricao_pk>/', views.validar_homologar_inscricoes_desportivas),
    path('listar_minhas_inscricoes/', views.listar_minhas_inscricoes),
    path('efetivar_inscricao_em_curso_suap/', views.efetivar_inscricao_em_curso_suap),
    path('cancelar_inscricao_em_curso_suap/', views.cancelar_inscricao_em_curso_suap),
    path('efetivar_inscricao_em_curso_procdoc/', views.efetivar_inscricao_em_curso_procdoc),
    path('cancelar_inscricao_em_curso_procdoc/', views.cancelar_inscricao_em_curso_procdoc),
    path('enviar_email_confirmacao/<int:inscricao_id>/', views.enviar_email_confirmacao),
    path('enviar_email_confirmacao_quem_nao_recebeu/', views.enviar_email_confirmacao_quem_nao_recebeu),
    path('enviar_email_teste/', views.enviar_email_teste),
    path('enviar_email_confirmacao_para_todos/', views.enviar_email_confirmacao_para_todos),
    path('enviar_email_confirmacao_para_quem_nao_confirmou/', views.enviar_email_confirmacao_para_quem_nao_confirmou),
]
