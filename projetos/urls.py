from django.urls import path

from projetos import views

urlpatterns = [
    path('meus_projetos/', views.meus_projetos),
    path('editais_abertos/', views.editais_abertos),
    path('pre_avaliacao/', views.pre_avaliacao),
    path('avaliacao/', views.avaliacao),
    path('projetos_pre_aprovados/<int:edital_id>/<int:uo_id>/', views.projetos_pre_aprovados),
    path('projetos_nao_avaliados/<int:edital_id>/', views.projetos_nao_avaliados),
    path('projeto/<int:projeto_id>/', views.projeto),
    path('imprimir_projeto/<int:projeto_id>/', views.imprimir_projeto),
    path('relatorio_projeto/<int:projeto_id>/', views.relatorio_projeto),
    path('memoria_calculo/<int:projeto_id>/', views.memoria_calculo),
    path('edital/<int:edital_id>/', views.edital),
    path('pre_aprovar/<int:projeto_id>/', views.pre_aprovar),
    path('pre_rejeitar/<int:projeto_id>/', views.pre_rejeitar),
    path('pre_selecionar/<int:projeto_id>/', views.pre_selecionar),
    path('avaliar/<int:projeto_id>/', views.avaliar),
    path('visualizar_ficha_avaliacao/<int:avaliacao_id>/', views.visualizar_ficha_avaliacao),
    path('projetos_em_execucao/', views.projetos_em_execucao),
    path('adicionar_participante_aluno/<int:projeto_id>/', views.adicionar_participante_aluno),
    path('adicionar_participante_servidor/<int:projeto_id>/', views.adicionar_participante_servidor),
    path('editar_participante_aluno/<int:projeto_id>/<int:participacao_id>/', views.editar_participante_aluno),
    path('editar_participante_servidor/<int:projeto_id>/<int:participacao_id>/', views.editar_participante_servidor),
    path('alterar_coordenador/<int:projeto_id>/', views.alterar_coordenador),
    path('remover_participante/<int:participacao_id>/', views.remover_participante),
    path('adicionar_meta/<int:projeto_id>/', views.adicionar_meta),
    path('editar_meta/<int:meta_id>/', views.editar_meta),
    path('remover_meta/<int:meta_id>/', views.remover_meta),
    path('adicionar_etapa/<int:meta_id>/', views.adicionar_etapa),
    path('editar_etapa/<int:etapa_id>/', views.editar_etapa),
    path('editar_equipe_etapa/<int:etapa_id>/', views.editar_equipe_etapa),
    path('remover_etapa/<int:etapa_id>/', views.remover_etapa),
    path('registro_execucao_etapa/<int:etapa_id>/', views.registro_execucao_etapa),
    path('validar_execucao_etapa/<int:projeto_id>/', views.validar_execucao_etapa),
    path('reprovar_execucao_etapa/<int:registroexecucaoetapa_id>/', views.reprovar_execucao_etapa),
    path('reprovar_execucao_gasto/<int:registroexecucaogasto_id>/', views.reprovar_execucao_gasto),
    path('adicionar_desembolso/<int:projeto_id>/', views.adicionar_desembolso),
    path('editar_desembolso/<int:desembolso_id>/', views.editar_desembolso),
    path('remover_desembolso/<int:desembolso_id>/', views.remover_desembolso),
    path('adicionar_foto/<int:projeto_id>/', views.adicionar_foto),
    path('remover_foto/<int:foto_id>/', views.remover_foto),
    path('upload_anexo/<int:anexo_id>/', views.upload_anexo),
    path('adicionar_anexo_do_projeto/<int:participacao_id>/', views.adicionar_anexo_do_projeto),
    path('upload_anexo_auxiliar/<int:anexo_id>/', views.upload_anexo_auxiliar),
    path('upload_edital/<int:edital_id>/', views.upload_edital),
    path('visualizar_arquivo/<int:arquivo_id>/', views.visualizar_arquivo),
    path('registro_gasto/<int:item_id>/', views.registro_gasto),
    path('registro_conclusao/<int:projeto_id>/', views.registro_conclusao),
    path('ativar_participante/<int:participacao_id>/', views.ativar_participante),
    path('historico_equipe/<int:participacao_id>/', views.historico_equipe),
    path('concluir_planejamento/<int:projeto_id>/', views.concluir_planejamento),
    path('finalizar_conclusao/<int:projeto_id>/', views.finalizar_conclusao),
    path('gerenciar_historico_projeto/<int:projeto_id>/', views.gerenciar_historico_projeto),
    path('adicionar_recurso/<int:edital_id>/', views.adicionar_recurso),
    path('editar_recurso/<int:recurso_id>/', views.editar_recurso),
    path('remover_recurso/<int:recurso_id>/', views.remover_recurso),
    path('adicionar_criterio_avaliacao/<int:pk>/', views.adicionar_criterio_avaliacao),
    path('editar_criterio_avaliacao/<int:pk>/', views.editar_criterio_avaliacao),
    path('remover_criterio_avaliacao/<int:pk>/', views.remover_criterio_avaliacao),
    path('adicionar_oferta_projeto/<int:edital_id>/', views.adicionar_oferta_projeto),
    path('editar_oferta_projeto/<int:oferta_projeto_id>/<int:edital_id>/', views.editar_oferta_projeto),
    path('remover_oferta_projeto/<int:oferta_projeto_id>/<int:edital_id>/', views.remover_oferta_projeto),
    path('adicionar_anexo/<int:edital_id>/', views.adicionar_anexo),
    path('editar_anexo/<int:anexo_id>/', views.editar_anexo),
    path('editar_projeto/<int:projeto_id>/', views.editar_projeto),
    path('adicionar_projeto/<int:edital_id>/', views.adicionar_projeto),
    path('remover_anexo/<int:anexo_id>/', views.remover_anexo),
    path('adicionar_anexo_auxiliar/<int:edital_id>/', views.adicionar_anexo_auxiliar),
    path('editar_anexo_auxiliar/<int:anexo_id>/', views.editar_anexo_auxiliar),
    path('remover_anexo_auxiliar/<int:anexo_id>/', views.remover_anexo_auxiliar),
    path('avaliar_conclusao_projeto/<int:registro_id>/', views.avaliar_conclusao_projeto),
    path('relatorio_dimensao_extensao/', views.relatorio_dimensao_extensao),
    path('adicionar_caracterizacao_beneficiario/<int:projeto_id>/', views.adicionar_caracterizacao_beneficiario),
    path('editar_caracterizacao_beneficiario/<int:caracterizacao_beneficiario_id>/', views.editar_caracterizacao_beneficiario),
    path('remover_caracterizacao_beneficiario/<int:caracterizacao_beneficiario_id>/', views.remover_caracterizacao_beneficiario),
    path('pre_avaliacao/selecionar_avaliadores/', views.pre_avaliacao),
    path('reabrir_projeto/<int:projeto_id>/', views.reabrir_projeto),
    path('plano_trabalho_participante/<int:projeto_id>/<int:participacao_id>/', views.plano_trabalho_participante),
    path('adicionar_licao_aprendida/<int:projeto_id>/', views.adicionar_licao_aprendida),
    path('relatorio_licoes_aprendidas/', views.relatorio_licoes_aprendidas),
    path('excluir_avaliacao/<int:avaliacao_id>/', views.excluir_avaliacao),
    path('adicionar_oferta_projeto_por_tema/<int:edital_id>/', views.adicionar_oferta_projeto_por_tema),
    path('editar_oferta_projeto_por_tema/<int:oferta_projeto_id>/<int:edital_id>/', views.editar_oferta_projeto_por_tema),
    path('remover_oferta_projeto_por_tema/<int:oferta_projeto_id>/<int:edital_id>/', views.remover_oferta_projeto_por_tema),
    path('lista_email_coordenadores/', views.lista_email_coordenadores),
    path('listar_equipes_dos_projetos/', views.listar_equipes_dos_projetos),
    path('emitir_certificado_extensao_pdf/<int:pk>/', views.emitir_certificado_extensao_pdf),
    path('cancelar_projeto/<int:projeto_id>/', views.cancelar_projeto),
    path('solicitacoes_de_cancelamento/', views.solicitacoes_de_cancelamento),
    path('avaliar_cancelamento_projeto/<int:cancelamento_id>/', views.avaliar_cancelamento_projeto),
    path('editais_para_avaliacao/', views.editais_para_avaliacao),
    path('selecionar_avaliadores/<int:edital_id>/', views.selecionar_avaliadores),
    path('selecionar_avaliadores_do_projeto/<int:projeto_id>/', views.selecionar_avaliadores_do_projeto),
    path('lista_emails_comissao/<int:comissao_id>/', views.lista_emails_comissao),
    path('emitir_declaracao_avaliador/', views.emitir_declaracao_avaliador),
    path('emitir_declaracao_avaliador_pdf/<int:pk>/', views.emitir_declaracao_avaliador_pdf),
    path('indicar_pre_avaliador/', views.indicar_pre_avaliador),
    path('selecionar_pre_avaliador/<int:edital_id>/', views.selecionar_pre_avaliador),
    path('selecionar_pre_avaliador_do_projeto/<int:projeto_id>/', views.selecionar_pre_avaliador_do_projeto),
    path('gerenciar_monitores/', views.gerenciar_monitores),
    path('selecionar_monitor/<int:edital_id>/', views.selecionar_monitor),
    path('selecionar_monitor_do_projeto/<int:projeto_id>/', views.selecionar_monitor_do_projeto),
    path('registro_beneficiario_atendido/<int:caracterizacao_id>/', views.registro_beneficiario_atendido),
    path('adicionar_anexo_diverso_projeto/<int:projeto_id>/', views.adicionar_anexo_diverso_projeto),
    path('prestacao_contas/<int:projeto_id>/', views.prestacao_contas),
    path('adicionar_extrato_mensal/<int:projeto_id>/', views.adicionar_extrato_mensal),
    path('adicionar_termo_cessao/<int:projeto_id>/', views.adicionar_termo_cessao),
    path('resultado_edital/<int:periodo>/', views.resultado_edital),
    path('divulgar_resultado_edital/<int:edital_id>/<int:periodo>/', views.divulgar_resultado_edital),
    path('enviar_recurso/<int:projeto_id>/', views.enviar_recurso),
    path('avaliar_recurso_projeto/<int:recurso_id>/', views.avaliar_recurso_projeto),
    path('recurso_projeto/<int:recurso_id>/', views.recurso_projeto),
    path('solicitacoes_de_recurso/', views.solicitacoes_de_recurso),
    path('alterar_ficha_avaliacao/<int:itemavaliacao_id>/', views.alterar_ficha_avaliacao),
    path('ver_alteracao_ficha_avaliacao/<int:itemavaliacao_id>/', views.ver_alteracao_ficha_avaliacao),
    path('upload_outro_anexo/<int:anexo_id>/', views.upload_outro_anexo),
    path('excluir_outro_anexo/<int:anexo_id>/', views.excluir_outro_anexo),
    path('emitir_declaracao_orientacao_pdf/<int:pk>/', views.emitir_declaracao_orientacao_pdf),
    path('lista_email_avaliadores/', views.lista_email_avaliadores),
    path('listar_projetos_em_atraso/', views.listar_projetos_em_atraso),
    path('listar_avaliadores_de_projetos/', views.listar_avaliadores_de_projetos),
    path('avaliacoes_aluno/<int:participacao_id>/', views.avaliacoes_aluno),
    path('adicionar_avaliacao_aluno/<int:participacao_id>/', views.adicionar_avaliacao_aluno),
    path('ver_avaliacao_aluno/<int:avaliacao_id>/', views.ver_avaliacao_aluno),
    path('registrar_consideracoes_aluno/<int:avaliacao_id>/', views.registrar_consideracoes_aluno),
    path('ver_alteracoes_data/<int:projeto_id>/', views.ver_alteracoes_data),
    path('deletar_participante/<int:participacao_id>/', views.deletar_participante),
    path('editar_extrato_mensal/<int:extrato_id>/', views.editar_extrato_mensal),
    path('excluir_extrato_mensal/<int:extrato_id>/', views.excluir_extrato_mensal),
    path('editar_termo_cessao/<int:termo_id>/', views.editar_termo_cessao),
    path('excluir_termo_cessao/<int:termo_id>/', views.excluir_termo_cessao),
    path('filtrar_editais_por_ano/', views.filtrar_editais_por_ano),
    path('adicionar_comprovante_gru/<int:projeto_id>/', views.adicionar_comprovante_gru),
    path('excluir_comprovante_gru/<int:projeto_id>/', views.excluir_comprovante_gru),
    path('adicionar_tema_edital/<int:edital_id>/', views.adicionar_tema_edital),
    path('remover_tema_edital/<int:edital_id>/<int:tema_id>/', views.remover_tema_edital),
    path('indicar_areas_tematicas_de_interesse/', views.indicar_areas_tematicas_de_interesse),
    path('indicar_orientador/<int:participacao_id>/', views.indicar_orientador),
    path('editais/', views.editais),
    path('excluir_registro_execucao_etapa/<int:etapa_id>/', views.excluir_registro_execucao_etapa),
    path('cancelar_avaliacao_etapa/<int:registroexecucao_id>/', views.cancelar_avaliacao_etapa),
    path('cancelar_avaliacao_gasto/<int:registrogasto_id>/', views.cancelar_avaliacao_gasto),
    path('ver_plano_trabalho/<int:projeto_id>/<int:participacao_id>/', views.ver_plano_trabalho),
    path('desvincular_participante_atividades/<int:participacao_id>/', views.desvincular_participante_atividades),
    path('listar_avaliadores/', views.listar_avaliadores),
    path('salvar_temas_edital/<int:edital_id>/', views.salvar_temas_edital),
    path('validar_projeto_externo/<int:projeto_id>/<str:opcao>/', views.validar_projeto_externo),
    path('estatisticas/', views.estatisticas),
    path('inativar_projeto/<int:projeto_id>/', views.inativar_projeto),
    path('adicionar_participante_colaborador/<int:projeto_id>/', views.adicionar_participante_colaborador),
    path('editar_participante_colaborador/<int:projeto_id>/<int:participacao_id>/', views.editar_participante_colaborador),
    path('clonar_projeto/<int:edital_id>/', views.clonar_projeto),
    path('clonar_etapa/<int:meta_id>/', views.clonar_etapa),
    path('cancelar_pre_avaliacao_projeto/<int:projeto_id>/', views.cancelar_pre_avaliacao_projeto),
    path('relatorio_caracterizacao_beneficiarios/', views.relatorio_caracterizacao_beneficiarios),
    path('emitir_declaracao_participacao_pdf/<int:pk>/', views.emitir_declaracao_participacao_pdf),
    path('reativar_projeto/<int:projeto_id>/', views.reativar_projeto),
    path('excluir_desembolsos/<int:projeto_id>/', views.excluir_desembolsos),
    path('cadastrar_frequencia/<int:projeto_id>/', views.cadastrar_frequencia),
    path('validar_frequencia/<int:registrofrequencia_id>/', views.validar_frequencia),
    path('gerar_lista_frequencia/<int:projeto_id>/', views.gerar_lista_frequencia),
    path('validar_registros_frequencia/<int:projeto_id>/', views.validar_registros_frequencia, name="validar_registros_frequencia"),
    path('editar_frequencia/<int:registrofrequencia_id>/', views.editar_frequencia),
    path('excluir_frequencia/<int:registrofrequencia_id>/', views.excluir_frequencia),
    path('aceitar_termo_compromisso/<int:participacao_id>/', views.aceitar_termo_compromisso),
    path('alterar_chefia_imediata_participacao/<int:participacao_id>/', views.alterar_chefia_imediata_participacao),
    path('participacoes_pendentes_anuencia/', views.participacoes_pendentes_anuencia),
    path('registrar_anuencia_participacao/<int:participacao_id>/<str:opcao>/', views.registrar_anuencia_participacao),
    path('cancelar_anuencia/<int:participacao_id>/', views.cancelar_anuencia),
    path('cadastrar_dados_bancarios/<int:participacao_id>/', views.cadastrar_dados_bancarios),
    path('autorizar_edital/<int:edital_id>/<str:opcao>/', views.autorizar_edital),
]
