from django.urls import path

from ponto import views

urlpatterns = [
    path('observacao_adicionar/<str:data_observacao>/', views.observacao_adicionar),
    path('observacao_editar/<int:observacao_id>/', views.observacao_editar),
    path('observacao_remover/<int:observacao_id>/', views.observacao_remover),
    # FREQUENCIAS
    path('frequencia_noturna_extra/', views.frequencia_noturna),
    path('frequencia_noturna_csv/', views.frequencia_noturna_csv),
    path('frequencia_terceirizados_setor/', views.frequencia_terceirizados_setor),
    path('frequencia_terceirizados/', views.frequencia_terceirizados),
    path('frequencia_funcionario/', views.frequencia_funcionario, name='frequencia_funcionario'),
    path('relatorio_frequencias_setor/', views.relatorio_frequencias_setor),
    path('frequencia_cargo_emprego/', views.frequencia_cargo_emprego),
    # URLs para os terminais de ponto
    path('get_dump_terminal_ponto/', views.get_dump_terminal_ponto),
    path('get_fotos_terminal_ponto/', views.get_fotos_terminal_ponto),
    path('adicionar_abono_inconsistencia_frequencia/<str:servidor_matricula>/<str:data_falta>/', views.adicionar_abono_inconsistencia_frequencia),
    path('abrir_compensacao_horario/<int:compensacao_horario_id>/', views.abrir_compensacao_horario),
    # path('validar_compensacao_horario/<int:compensacao_horario_id>/<int:validacao_valor>/', views.validar_compensacao_horario),
    path('editar_obs_compensacao_horario/<int:compensacao_horario_id>/', views.editar_obs_compensacao_horario),
    # path('auto_add_compensacao_horario/', views.auto_add_compensacao_horario),
    # path('validar_varias_compensacoes_horarios/', views.validar_varias_compensacoes_horarios),
    path('abrir_opcao_recesso/<int:recesso_opcao_id>/', views.abrir_opcao_recesso),
    path('excluir_opcao_recesso/<int:recesso_opcao_id>/', views.excluir_opcao_recesso),
    path('adicionar_data_de_recesso/<int:recesso_opcao_id>/', views.adicionar_dia_de_recesso),
    path('excluir_dia_de_recesso/<int:recesso_data_id>/', views.excluir_data_de_recesso),
    path('adicionar_periodo_de_compensacao/<int:recesso_opcao_id>/', views.adicionar_periodo_de_compensacao),
    path('excluir_periodo_de_compensacao/<int:periodo_de_compensacao_id>/', views.excluir_periodo_de_compensacao),
    path('definir_periodo_escolha_recesso/<int:recesso_opcao_id>/', views.definir_periodo_escolha_recesso),
    path('liberar_escolha_recesso/<int:recesso_opcao_id>/', views.liberar_escolha_recesso),
    path('retornar_a_fase_de_cadastro/<int:recesso_opcao_id>/', views.retornar_a_fase_de_cadastro),
    path('fechar_cadastro_e_escolha/<int:recesso_opcao_id>/', views.fechar_cadastro_e_escolha),
    path('escolher_dia_de_recesso/', views.escolher_dia_de_recesso),
    path('abrir_recesso_escolhido/<int:recesso_opcao_escolhida_id>/', views.abrir_recesso_escolhido),
    path('editar_dias_de_recesso_escolhidos/<int:recesso_opcao_escolhida_id>/', views.editar_dias_de_recesso_escolhidos),
    path('validar_recesso_escolhido/<int:recesso_opcao_escolhida_id>/', views.validar_recesso_escolhido),
    path('cancelar_validacao_recesso_escolhido/<int:recesso_opcao_escolhida_id>/', views.cancelar_validacao_recesso_escolhido),
    path('informar_compensacao/<str:periodo_inicio>/<str:periodo_fim>/', views.informar_compensacao),
    path('informar_compensacao_recesso/<str:periodo_inicio>/<str:periodo_fim>/', views.informar_compensacao_recesso),
    path('excluir_recesso_escolhido/<int:recesso_opcao_escolhida_id>/', views.excluir_recesso_escolhido),
    path('adicionar_compensacao/', views.adicionar_compensacao),
    path('detalhar_compensacao/<str:matricula>/<str:data>/', views.detalhar_compensacao),
    path('ver_frequencia/<str:matricula>/', views.ver_frequencia),
    path('remover_compensacoes/<str:matricula>/', views.remover_compensacoes),
    path('editar_chefe_recesso_escolhido/<int:recesso_opcao_escolhida_id>/', views.editar_chefe_recesso_escolhido),
    path('localizar_acompanhamentos/', views.localizar_acompanhamentos),
    path('editar_acompanhamento/<int:recesso_opcao_escolhida_id>/', views.editar_acompanhamento),
    path('ver_compensacao_detalhada/', views.ver_compensacao_detalhada),
    path('atualizar_lista_dias_efetivos_a_compensar/<int:recesso_opcao_escolhida_id>/', views.atualizar_lista_dias_efetivos_a_compensar),
    path('documento_anexar/<str:dia_ponto>/add/', views.documento_anexar_add),
    path('documento_anexar/<str:pk>/change/', views.documento_anexar_change),
    path('documento_anexar/<str:pk>/delete/', views.documento_anexar_delete),
    path('adicionar_abono_inconsistencia_frequencia_lote/', views.adicionar_abono_inconsistencia_frequencia_lote),
    path('ajax/get_frequencia_funcionario/', views.ajax_frequencia_funcionario),
    path('registrar_frequencia_online/', views.registrar_frequencia_online),

]