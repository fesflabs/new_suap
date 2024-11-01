from django.urls import path
from comum import views

urlpatterns = [
    path('feed_noticias/', views.feed_noticias),
    path('login_exige_captcha/<str:username>/', views.login_exige_captcha),
    path('selecionar_vinculo/', views.selecionar_vinculo, name='selecionar_vinculo'),
    path('telefones/', views.telefones),
    path('telefones_csv/', views.telefones_csv),
    path('admin/', views.admin),
    path('maquinas/', views.maquinas),
    path('maquinas/detalhes/<int:maquina_pk>/', views.maquinas_detalhes),
    path('configuracao/', views.configuracao),
    path('baixar_macro_siape/', views.baixar_macro_siape),
    path('baixar_macro_siape_historico_pca/', views.baixar_macro_siape_historico_pca),
    path('baixar_macro_siape_personalizavel/', views.baixar_macro_siape_personalizavel),
    path('setor_adicionar_telefone/<int:objeto_pk>/', views.setor_adicionar_telefone),
    path('setor_remover_telefone/<int:objeto_pk>/', views.setor_remover_telefone),
    path('fiscal_concurso/', views.fiscal_concurso),
    path('gerar_cvs/<int:id_documentocontroletipo>/', views.gerar_cvs),
    path('ver_arquivo_siafi/', views.ver_arquivo_siafi),
    path('get_pessoa/<str:username>/<str:versao>/', views.get_pessoa),
    path('get_pessoas/', views.get_pessoas),
    path('get_pessoas/<str:versao>/', views.get_pessoas),
    path('get_chave_publica_suap/', views.get_chave_publica_suap),
    path('get_fotos_funcionarios/', views.get_fotos_funcionarios),
    path('get_fotos_alunos/', views.get_fotos_alunos),
    path('acessibilidade/', views.acessibilidade),
    path('guia/', views.guia),
    path('temas/', views.temas),
    path('alterar_tema/', views.alterar_tema),
    path('alterar_senha/', views.alterar_senha),
    path('solicitar_trocar_senha/', views.solicitar_trocar_senha),
    path('trocar_senha/<str:username>/<str:token>/', views.trocar_senha),
    path('autenticar_documento/', views.autenticar_documento),
    path('baixar_documento/<int:pk>/<str:codigo_verificador>/', views.baixar_documento),
    path('grupos_usuarios/', views.grupos_usuarios),
    path('gerenciamento_grupo/', views.gerenciamento_grupo),
    path('adicionar_usuario_grupo/<int:pk_grupo>/', views.adicionar_usuario_grupo),
    path('remover_usuario_grupo/<int:pk_usuario_grupo>/', views.remover_usuario_grupo),
    path('adicionar_setor_usuario_grupo/<pk_usuario_grupo>/', views.adicionar_setor_usuario_grupo),
    path('grupos_usuario/<int:usuario_pk>/', views.grupos_usuario),
    path('minha_conta/', views.minha_conta),
    path('comentario/add/<str:aplicacao>/<str:modelo>/<int:objeto_id>/', views.comentario_add),
    path('comentario/add/<str:aplicacao>/<str:modelo>/<int:objeto_id>/<int:resposta_id>/', views.comentario_add),
    path('copiar_digital_de_outra_pessoa_mesmo_cpf/<int:pk_pessoa_fisica>/', views.copiar_digital_de_outra_pessoa_mesmo_cpf),
    path('sala/visualizar/<int:sala_pk>/', views.sala_visualizar),
    path('sala/solicitar_reserva/<int:sala_pk>/', views.sala_solicitar_reserva),
    path('sala/agenda_atual/<int:sala_pk>/', views.sala_agenda_atual),
    path('sala/informacoes_complementares/<int:sala_pk>/', views.sala_informacoes_complementares),
    path('sala/ver_solicitacao/<int:solicitacao_reserva_pk>/', views.sala_ver_solicitacao),
    path('sala/excluir_solicitacao/<int:solicitacao_reserva_pk>/', views.sala_excluir_solicitacao),
    path('sala/avaliar_solicitacao/<int:solicitacao_reserva_pk>/', views.sala_avaliar_solicitacao),
    path('sala/cancelar_solicitacao/<int:solicitacao_reserva_pk>/', views.sala_cancelar_solicitacao),
    path('sala/listar_indisponibilizacoes/', views.sala_listar_indisponibilizacoes),
    path('sala/indicadores/', views.sala_indicadores),
    path('sala/registrar_indisponibilizacao/', views.sala_registrar_indisponibilizacao),
    path('sala/registrar_indisponibilizacao/<int:sala_pk>/', views.sala_registrar_indisponibilizacao),
    path('sala/ver_indisponibilizacao/<int:indisponibilizacao_pk>/', views.sala_ver_indisponibilizacao),
    path('sala/excluir_indisponibilizacao/<int:indisponibilizacao_pk>/', views.sala_excluir_indisponibilizacao),
    path('sala/cancelar_reserva/<int:reserva_pk>/', views.sala_cancelar_reserva),
    path('sala/informar_ocorrencia/<int:reserva_pk>/', views.sala_informar_ocorrencia_reserva),
    path('sala/cancelar_reservas_periodo/<int:sala_pk>/', views.sala_cancelar_reservas_periodo),
    path('expandir_menu/', views.expandir_menu),
    path('retrair_menu/', views.retrair_menu),
    path('atualizar_email_secundario/<int:vinculo_pk>/', views.atualizar_email),
    path('pessoa_fisica/<int:pessoa_fisica_pk>/adicionar_contato_de_emergencia', views.adicionar_contato_de_emergencia),
    path('pessoa_fisica/<int:pessoa_fisica_pk>/listar_contatos_de_emergencia', views.listar_contatos_de_emergencia),
    path('excluir/<str:app>/<str:model>/<str:pks>/', views.excluir),
    path('popula_nome_sugerido/', views.popula_nome_sugerido),
    path('ver_solicitacao_documento/<int:solicitacaodocumento_pk>/', views.ver_solicitacao_documento),
    path('marcar_solicitacao_atendida/<int:solicitacaodocumento_pk>/', views.marcar_solicitacao_atendida),
    path('rejeitar_solicitacao/<int:solicitacaodocumento_pk>/', views.rejeitar_solicitacao),
    path('pensionista/<str:matricula_pensionista>/', views.tela_pensionista),
    path('usuario/<int:usuario_id>/historico_grupos/', views.usuario_historico_grupos),
    path('usuarios_ativos/', views.usuarios_ativos),
    path('index/layout/', views.atualiza_layout),
    path('index/esconder_quadro/', views.esconder_quadro),
    path('index/exibir_quadro/', views.exibir_quadro),
    path('prestador_servico/<int:id>/', views.prestador_servico, name='prestador_servico'),
    path('ocupacao_prestador/<int:prestador_id>/', views.ocupacao_prestador),
    path('publico/<int:id>/visualizar/', views.visualizar_publico, name='comum_visualizar_publico'),
    path('documentacao/', views.documentacao_view),
    path('documentacao/bpmn/<str:aplicacao>/<str:bpmn>/', views.documentacao_bpmn_view),
    path('documentacao/cenario/<str:aplicacao>/<str:funcionalidade>/<str:cenario>/', views.documentacao_cenario_view),
    path('documentacao/about/<str:aplicacao>/', views.about_view),
    path('documentacao/about_feature/<str:aplicacao>/<str:funcionalidade>/', views.about_feature_view),
    path('documentacao/imagem/', views.documentacao_imagem_view),
    path('manuais/', views.manuais_view),
    path('baixar_manuais/<str:aplicacao>/<str:versao>/', views.baixar_manuais),
    path('calendario_administrativo/', views.calendario_administrativo),
    path('remote_logout/<int:sessioninfo_pk>/', views.remote_logout),
    path('remote_logout_all/', views.remote_logout_all),
    path('deactivate_device/<int:device_pk>/', views.deactivate_device),
    path('reactivate_device/<int:device_pk>/', views.reactivate_device),
    path('give_nickname_to_device/<int:device_pk>/', views.give_nickname_to_device),
    path('webmail/', views.webmail),
    path('azure/', views.azure),
    path('google_classroom/', views.google_classroom),
    path('documentos_emitidos_suap/', views.documentos_emitidos_suap),
    path('notificacoes/', views.notificacoes),
    path('notificacao/<int:pk>/', views.notificacao),
    path('busca_notificacao/<int:counter>/', views.busca_notificacao),
    path('ativar_categoria_notificacao/<int:pk>/', views.ativar_categoria_notificacao),
    path('desativar_categoria_notificacao/<int:pk>/', views.desativar_categoria_notificacao),
    path('atualizar_preferencia_padrao/', views.atualizar_preferencia_padrao),
    path('atualizar_via_suap/<int:pk>/', views.atualizar_via_suap),
    path('ativar_via_suap_em_lote/', views.ativar_via_suap_em_lote),
    path('desativar_via_suap_em_lote/', views.desativar_via_suap_em_lote),
    path('ativar_via_email_em_lote/', views.ativar_via_email_em_lote),
    path('desativar_via_email_em_lote/', views.desativar_via_email_em_lote),
    path('atualizar_via_email/<int:pk>/', views.atualizar_via_email),
    path('marcar_como_lida/<int:pk>/', views.marcar_como_lida),
    path('marcar_todas_notificacoes_como_lidas/', views.marcar_todas_notificacoes_como_lidas, name='marcar_todas_notificacoes_como_lidas'),
    path('excluir_notificacoes_antigas/', views.excluir_notificacoes_antigas),
    path('marcar_como_lida_em_lote/', views.marcar_como_lida_em_lote),
    path('marcar_como_nao_lida/<int:pk>/', views.marcar_como_nao_lida),
    path('marcar_como_nao_lida_em_lote/', views.marcar_como_nao_lida_em_lote),
    path('remover_notificacao/<int:pk>/', views.remover_notificacao),
    path('remover_notificacoes_em_lote/', views.remover_notificacoes_em_lote),
    path('novo_usuario_externo/', views.cadastrar_usuario_externo),
    path('novo_usuario_externo/<int:pessoafisica_id>/', views.cadastrar_usuario_externo),
    path('usuario_externo/<int:pk>/', views.usuario_externo),
    path('usuario_externo/ativar/<int:pk>/', views.ativar_usuario_externo),
    path('usuario_externo/inativar/<int:pk>/', views.inativar_usuario_externo),
    path('assinar_documento/', views.assinar_documento),
    path('verificar_documento/', views.verificar_documento),
    path('validar_assinatura/', views.validar_assinatura),
    path('predio/<int:pk>/', views.predio),
]
