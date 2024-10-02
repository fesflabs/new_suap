# -*- coding: utf-8 -*
from django.urls import path
from frota import views, relatorio

urlpatterns = [
    path('agendamento/<int:agendamento_id>/', views.agendamento),
    path('avaliar_agendamento_viagem/<int:agendamento_id>/', views.avaliar_agendamento_viagem),
    path('viagens_agendadas/', views.viagens_agendadas),
    path('saida_viagem/<int:resp_agendamento_id>/', views.saida_viagem),
    path('viagens_iniciadas/', views.viagens_iniciadas),
    path('chegada_viagem/<int:viagem_id>/', views.chegada_viagem),
    path('viagens/', views.viagens),
    path('viagem/<int:viagem_id>/', views.viagem),
    path('pdf_requisicao/<int:viagem_id>/', views.pdf_requisicao),
    path('viatura/<int:viatura_id>/', views.viatura),
    path('viagem_retroativa/', views.viagem_retroativa),
    path('ordem_abastecimento/<int:viagem_id>/', views.ordem_abastecimento),
    path('estatisticas_viaturas/', views.estatisticas_viaturas),
    path('estatisticas_deslocamento/', views.estatisticas_deslocamento),
    path('viagens_por_viatura/', views.viagens_por_viatura),
    path('estatistica_viagens_por_campus_setor/', views.estatistica_viagens_por_campus_setor),
    path('manutencaoviatura/<int:servico_id>/', views.manutencaoviatura),
    path('ver_calendario_agendamento/', views.ver_calendario_agendamento),
    path('autorizar_agendamento/<int:agendamento_id>/<str:opcao>/', views.autorizar_agendamento),
    path('controle_revisoes_viaturas/', views.controle_revisoes_viaturas),
    path('editar_proxima_revisao_viatura/<int:viatura_id>/', views.editar_proxima_revisao_viatura),
]

urlpatterns += [
    path('relatorio_viaturas/', relatorio.relatorio_viaturas),
    path('relatorio_motoristas_temporarios/', relatorio.relatorio_motoristas_temporarios),
    path('relatorio_solicitacoes_por_pessoa/', relatorio.relatorio_solicitacoes_por_pessoa),
    path('relatorio_deslocamento_por_viatura/', relatorio.relatorio_deslocamento_por_viatura),
    path('relatorio_consumo_por_maquina/', relatorio.relatorio_consumo_por_maquina),
    path('relatorio_viagens_por_motorista/', relatorio.relatorio_viagens_por_motorista),
]
