from django.urls import path

from centralservicos import views

urlpatterns = [
    path('listar_area_servico/', views.listar_area_servico),
    path('selecionar_servico_abertura/<slug:slug>/', views.selecionar_servico_abertura_chamado, name='centralservicos_selecionar_servico_abertura'),
    path('abrir_chamado/<int:servico_id>/', views.abrir_chamado, name='centralservicos_abrir_chamado'),
    path('indicadores/', views.indicadores),
    path('atendimentos_por_ano/', views.atendimentos_por_ano),
    path('relatorio_atendentes/', views.relatorio_atendentes),
    path('dashboard/', views.dashboard),
    path('meus_chamados/', views.meus_chamados),
    path('listar_chamados_suporte/', views.listar_chamados_suporte),
    path('reabrir_chamado/<int:chamado_id>/', views.reabrir_chamado),
    path('suspender_chamado/<int:chamado_id>/', views.suspender_chamado),
    path('escalar_atendimento_chamado/<int:chamado_id>/', views.escalar_atendimento_chamado),
    path('retornar_atendimento_chamado/<int:chamado_id>/', views.retornar_atendimento_chamado),
    path('chamado/<int:chamado_id>/', views.visualizar_chamado),
    path('monitoramento/<slug:token>/', views.monitoramento, name='centralservicos_monitoramento'),
    path('baseconhecimento/', views.baseconhecimento_listar_area_servico, name='centralservicos_baseconhecimento_listar_area_servico'),
    path('baseconhecimento/dashboard/<slug:slug>/', views.baseconhecimento, name='centralservicos_baseconhecimento'),
    path('baseconhecimento/<int:baseconhecimento_id>/', views.visualizar_baseconhecimento, name='centralservicos_visualizar_baseconhecimento'),
    path('baseconhecimento/unificar/', views.unificar_basesconhecimento),
    path('baseconhecimento/revisar/', views.revisar_basesconhecimento),
    path('baseconhecimento/aprovar/<int:baseconhecimento_id>/', views.aprovar_baseconhecimento, name='centralservicos_aprovar_baseconhecimento'),
    path('baseconhecimento/marcar_para_correcao/<int:baseconhecimento_id>/', views.marcar_baseconhecimento_para_correcao),
    path('baseconhecimento/publica/<int:baseconhecimento_id>/', views.visualizar_baseconhecimento_publica, name='centralservicos_visualizar_baseconhecimento_publica'),
    path('baseconhecimento/chamados/<int:baseconhecimento_id>/', views.baseconhecimento_chamados_resolvidos, name='centralservicos_baseconhecimento_chamados_resolvidos'),
    path('baseconhecimento/avaliar/<int:baseconhecimento_id>/<int:pergunta_id>/<int:nota>/',
         views.avaliar_baseconhecimento,
         name='centralservicos_avaliar_baseconhecimento',
         ),
    path('baseconhecimento/remover_anexo/<int:baseconhecimento_id>/<int:baseconhecimento_anexo_id>/',
         views.remover_anexo_baseconhecimento,
         name='centralservicos_remover_anexo_baseconhecimento',
         ),
    path('adicionar_anexo/<int:chamado_id>/', views.adicionar_anexo),
    path('adicionar_comentario/<int:chamado_id>/', views.adicionar_comentario),
    path('desconsiderar_comentario/<int:comentario_id>/', views.desconsiderar_comentario, name='centralservicos_desconsiderar_comentario'),
    path('adicionar_nota_interna/<int:chamado_id>/', views.adicionar_nota_interna),
    path('adicionar_outros_interessados/<int:chamado_id>/', views.adicionar_outros_interessados),
    path('adicionar_grupo_de_interessados/<int:chamado_id>/', views.adicionar_grupo_de_interessados, name='centralservicos_adicionar_grupo_de_interessados'),
    path('remover_outros_interessados/<int:chamado_id>/<int:usuario_id>/', views.remover_outros_interessados),
    path('resolver_chamado/<int:chamado_id>/<int:baseconhecimento_id>/', views.resolver_chamado),
    path('auto_atribuir_chamado/<int:chamado_id>/', views.auto_atribuir_chamado, name='centralservicos_auto_atribuir_chamado'),
    path('atribuir_chamado/<int:chamado_id>/', views.atribuir_chamado),
    path('reclassificar_chamado/<int:chamado_id>/', views.reclassificar_chamado),
    path('cancelar_chamado/<int:chamado_id>/', views.cancelar_chamado, name='centralservicos_cancelar_chamado'),
    path('colocar_em_atendimento/<int:chamado_id>/', views.colocar_em_atendimento, name='centralservicos_colocar_em_atendimento'),
    path('resolver_chamado/<int:chamado_id>/', views.resolver_chamado, name='centralservicos_resolver_chamado'),
    path('fechar_chamado/<int:chamado_id>/', views.fechar_chamado),
    path('visualizar_chamados_semelhantes/<int:chamado_id>/', views.visualizar_chamados_semelhantes, name='centralservicos_visualizar_chamados_semelhantes'),
    path('visualizar_solucoes/<int:servico_id>/', views.visualizar_solucoes, name='centralservicos_visualizar_solucoes'),
    path('visualizar_outros_chamados_do_interessado/<int:chamado_id>/',
         views.visualizar_outros_chamados_do_interessado,
         name='centralservicos_visualizar_outros_chamados_do_interessado',
         ),
    path('adicionar_tags_ao_chamado/<int:chamado_id>/', views.adicionar_tags_ao_chamado, name='centralservicos_adicionar_tags_ao_chamado'),
    path('remover_tag_do_chamado/<int:chamado_id>/<int:tag_id>/', views.remover_tag_do_chamado, name='centralservicos_remover_tag_do_chamado'),
    path('get_centros_atendimento_por_servico_e_campus/<int:servico_id>/<int:campus_id>/',
         views.get_centros_atendimento_por_servico_e_campus,
         name='centralservicos_get_centros_atendimento_por_servico_e_campus',
         ),
    path('get_centros_atendimento_por_area/<int:area_id>/', views.get_centros_atendimento_por_area, name='centralservicos_get_centros_atendimento_por_area'),
    path('get_campus_com_centros_atendimento/<int:servico_id>/<int:chamado_id>/',
         views.get_campus_com_centros_atendimento,
         name='centralservicos_get_campus_com_centros_atendimento',
         ),
    # Autocomplete
    path('ac_interessado/', views.ac_interessado, name='centralservicos_ac_interessado'),
]