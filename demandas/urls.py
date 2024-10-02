from django.urls import path

from demandas import views

urlpatterns = [
    path('visualizar/<int:demanda_id>/', views.visualizar, name='demanda_visualizar'),
    path('adicionar_anexo/<int:demanda_id>/', views.adicionar_anexo, name='demanda_anexos_adicionar'),
    path('remover_anexo/<int:anexo_id>/', views.remover_anexo, name='demanda_anexos_remover'),
    path('dod/<int:demanda_id>/<int:dod_id>/', views.dod_alterar, name='dod_alterar'),
    path('dod/<int:demanda_id>/<int:dod_id>/fechar/', views.dod_fechar, name='dod_fechar'),
    path('dod/<int:demanda_id>/<int:dod_id>/aprovar/', views.dod_aprovar, name='dod_aprovar'),
    path('dod/<int:demanda_id>/<int:dod_id>/reprovar/', views.dod_reprovar, name='dod_reprovar'),
    path('especificacao/<int:demanda_id>/<int:dod_id>/add/', views.especificacao_add_change, name='dod_especificacao_add'),
    path('especificacao/<int:demanda_id>/<int:dod_id>/<int:especificacao_id>/change/', views.especificacao_add_change, name='dod_especificacao_change'),
    path('especificacao/<int:demanda_id>/<int:dod_id>/<int:especificacao_id>/delete/', views.especificacao_delete, name='dod_especificacao_delete'),
    path('notainterna/<int:demanda_id>/add/', views.nota_interna_add_change, name='demanda_notainterna_add'),
    path('notainterna/<int:demanda_id>/<int:notainterna_id>/change/', views.nota_interna_add_change, name='demanda_notainterna_change'),
    path('notainterna/<int:demanda_id>/<int:notainterna_id>/delete/', views.nota_interna_delete, name='demanda_notainterna_delete'),
    path('alterar_situacao/<int:demanda_id>/<str:situacao>/', views.alterar_situacao, name='demanda_situacao_alterar'),
    path('especificacao_tecnica/<int:demanda_id>/', views.especificacao_tecnica, name='demanda_especificacao_tecnica'),
    path('editar_data_previsao_etapa/<int:demanda_id>/', views.editar_data_previsao_etapa, name='demanda_editar_data_previsao_etapa'),
    path('acompanhar/<int:demanda_id>/', views.acompanhar, name='acompanhar'),
    path('adicionar_observador/<int:demanda_id>/<int:user_id>/', views.adicionar_observador, name='adicionar_observador'),
    path('remover_observador/<int:demanda_id>/<int:user_id>/', views.remover_observador, name='remover_observador'),
    path('homologacao/<int:demanda_id>/aprovar/', views.homologacao_aprovar, name='homologacao_aprovar'),
    path('homologacao/<int:demanda_id>/reprovar/', views.homologacao_reprovar, name='homologacao_reprovar'),
    path('concordar_demanda/<int:demanda_id>/', views.concordar_demanda),
    path('discordar_demanda/<int:demanda_id>/', views.discordar_demanda),

    # Demandantes
    path('demandas_prioritarias_por_area/<int:pk_area>/', views.demandas_prioritarias_por_area, name='demandas_prioritarias_por_area'),
    path('atualizar_prioridade/<int:area_id>/', views.atualizar_prioridade, name='atualizar_prioridade'),

    # Gestão
    path('painel_forca_trabalho/', views.painel_forca_trabalho, name='painel_forca_trabalho'),
    path('painel_forca_trabalho_desenvolvedor/<int:desenvolvedor_id>/', views.painel_forca_trabalho_desenvolvedor, name='painel_forca_trabalho_desenvolvedor'),
    path('acompanhamento_demandas/', views.acompanhamento_demandas, name='acompanhamento_demandas'),
    path('acompanhamento_demandas_pdf/', views.acompanhamento_demandas_pdf, name='acompanhamento_demandas_pdf'),
    path('demandas/', views.demandas, name='demandas'),
    path('indicadores/', views.indicadores, name='demanda_indicadores'),
    path('relatorio/geral/', views.relatorio_geral, name='demanda_relatorio_geral'),
    path('glossario/', views.glossario, name='glossario'),
    path('atualizacao/<int:atualizacao_id>/', views.atualizacao, name='demanda_atualizacao'),
    path('atualizacoes/', views.atualizacoes, name='atualizacoes'),
    path('atualizar_prioridade_manualmente/<int:demanda_id>/', views.atualizar_prioridade_manualmente, name='atualizar_prioridade_manualmente'),
    path('analistadesenvolvedor/<int:pk>/', views.analistadesenvolvedor, name='analistadesenvolvedor'),

    # Ambientes de Homologação
    path('ambientehomologacao/<int:pk>/', views.ambientehomologacao, name='ambientehomologacao'),
    path('acessar_ambiente_via_demanda/<int:pk>/<int:demanda_pk>/', views.acessar_ambiente_via_demanda, name='acessar_ambiente_via_demanda'),
    path('executar_comando_ambiente_homologacao/<int:pk>/', views.executar_comando_ambiente_homologacao, name='executar_comando_ambiente_homologacao'),

    # Sugestão de Melhoria
    path('listar_areas_atuacao_sugestao_melhoria/', views.listar_areas_atuacao_sugestao_melhoria),
    path('adicionar_sugestao_melhoria/<int:area_atuacao_id>/', views.adicionar_sugestao_melhoria),
    path('sugestoes_modulo/<int:area_atuacao_id>/<int:modulo_id>/', views.sugestoes_modulo),
    path('sugestao_melhoria/<int:sugestao_melhoria_id>/', views.sugestao_melhoria, name='sugestao_melhoria'),
    path('concordar_sugestao/<int:sugestao_melhoria_id>/', views.concordar_sugestao),
    path('discordar_sugestao/<int:sugestao_melhoria_id>/', views.discordar_sugestao),
    path('tornar_se_interessado/<int:sugestao_melhoria_id>/', views.tornar_se_interessado),
    path('editar_dados_basicos_sugestao_melhoria/<int:sugestao_melhoria_id>/', views.editar_dados_basicos_sugestao_melhoria),
    path('editar_todos_dados_sugestao_melhoria/<int:sugestao_melhoria_id>/', views.editar_todos_dados_sugestao_melhoria),
    path('editar_area_atuacao/<int:sugestao_melhoria_id>/', views.editar_area_atuacao),
    path('atribuir_se_como_responsavel_sugestao_melhoria/<int:sugestao_melhoria_id>/', views.atribuir_se_como_responsavel_sugestao_melhoria),
    path('gerar_demanda_sugestao_melhoria/<int:sugestao_melhoria_id>/', views.gerar_demanda_sugestao_melhoria),
    path('alterar_situacao_sugestao/<int:sugestao_melhoria_id>/<int:situacao>/', views.alterar_situacao_sugestao, name='alterar_situacao_sugestao'),
]
