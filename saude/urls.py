from django.urls import path

from saude import views

urlpatterns = [
    # Prontuários
    path('prontuarios/', views.prontuarios, name="prontuarios"),
    path('prontuario/<int:id_vinculo>/', views.prontuario, name="prontuario"),
    # Avaliação Biomédica
    path('avaliacao_biomedica/<int:atendimento_id>/', views.avaliacao_biomedica, name="avaliacao_biomedica"),
    path('adicionar_sinaisvitais/<int:atendimento_id>/', views.adicionar_sinaisvitais, name="adicionar_sinaisvitais"),
    path('adicionar_antropometria/<int:atendimento_id>/', views.adicionar_antropometria, name="adicionar_antropometria"),
    path('adicionar_acuidadevisual/<int:atendimento_id>/', views.adicionar_acuidadevisual, name="adicionar_acuidadevisual"),
    path('adicionar_antecedentesfamiliares/<int:atendimento_id>/', views.adicionar_antecedentesfamiliares, name="adicionar_antecedentesfamiliares"),
    path('adicionar_processosaudedoenca/<int:atendimento_id>/', views.adicionar_processosaudedoenca, name="adicionar_processosaudedoenca"),
    path('adicionar_habitosdevida/<int:atendimento_id>/', views.adicionar_habitosdevida, name="adicionar_habitosdevida"),
    path('adicionar_desenvolvimentopessoal/<int:atendimento_id>/', views.adicionar_desenvolvimentopessoal, name="adicionar_desenvolvimentopessoal"),
    path('adicionar_examefisico/<int:atendimento_id>/', views.adicionar_examefisico, name="adicionar_examefisico"),
    path('adicionar_percepcaosaudebucal/<int:atendimento_id>/', views.adicionar_percepcaosaudebucal, name="adicionar_percepcaosaudebucal"),
    path('antropometria_valores_referencia/', views.antropometria_valores_referencia, name="antropometria_valores_referencia"),
    path('adicionar_informacao_adicional/<int:atendimento_id>/', views.adicionar_informacao_adicional, name="adicionar_informacao_adicional"),
    path('enviar_mensagem_aluno/<int:vinculo_id>/<int:atendimento_id>/', views.enviar_mensagem_aluno, name="enviar_mensagem_aluno"),

    # Atendimentos
    path('abrir_atendimento/<int:tipo_atendimento>/<int:prontuario_id>/<int:vinculo>/<int:vinculo_id>/', views.abrir_atendimento, name="abrir_atendimento"),
    path('fechar_atendimento/<int:atendimento_id>/', views.fechar_atendimento, name="fechar_atendimento"),
    path('cancelar_atendimento/<int:atendimento_id>/', views.cancelar_atendimento, name="cancelar_atendimento"),
    path('reabrir_atendimento/<int:atendimento_id>/', views.reabrir_atendimento, name="reabrir_atendimento"),
    # Atendimento Médico/Enfermagem
    path('atendimento_medico_enfermagem/<int:atendimento_id>/', views.atendimento_medico_enfermagem, name="atendimento_medico_enfermagem"),
    path('adicionar_motivo_atendimento/<int:atendimento_id>/', views.adicionar_motivo_atendimento, name="adicionar_motivo_atendimento"),
    path('adicionar_anamnese/<int:atendimento_id>/', views.adicionar_anamnese, name="adicionar_anamnese"),
    path('adicionar_intervencao_enfermagem/<int:atendimento_id>/', views.adicionar_intervencao_enfermagem, name="adicionar_intervencao_enfermagem"),
    path('adicionar_hipotese_diagnostica/<int:atendimento_id>/', views.adicionar_hipotese_diagnostica, name="adicionar_hipotese_diagnostica"),
    path('adicionar_conduta_medica/<int:atendimento_id>/', views.adicionar_conduta_medica, name="adicionar_conduta_medica"),
    path('editar_hipotese_diagnostica/<int:hipotese_diagnostica_id>/', views.editar_hipotese_diagnostica, name="editar_hipotese_diagnostica"),
    path('editar_conduta_medica/<int:conduta_medica_id>/', views.editar_conduta_medica, name="editar_conduta_medica"),
    # Atendimento Odontológico
    path('atendimento_odontologico/<int:atendimento_id>/', views.atendimento_odontologico, name="atendimento_odontologico"),
    path('adicionar_procedimento_odontologico/<int:atendimento_id>/', views.adicionar_procedimento_odontologico, name="adicionar_procedimento_odontologico"),
    path('adicionar_odontograma/<int:atendimento_id>/', views.adicionar_odontograma, name="adicionar_odontograma"),
    path('adicionar_exame_periodontal/<int:atendimento_id>/', views.adicionar_exame_periodontal, name="adicionar_exame_periodontal"),
    path('adicionar_exame_estomatologico/<int:atendimento_id>/', views.adicionar_exame_estomatologico, name="adicionar_exame_estomatologico"),
    path('indicar_procedimento/<int:plano_tratamento_id>/', views.indicar_procedimento, name="indicar_procedimento"),
    path('registrar_execucao_plano/<int:plano_tratamento_id>/', views.registrar_execucao_plano, name="registrar_execucao_plano"),
    path('excluir_intervencao/<int:atendimento_id>/', views.excluir_intervencao, name="excluir_intervencao"),
    path('adicionar_intervencao/<int:atendimento_id>/', views.adicionar_intervencao, name="adicionar_intervencao"),
    path('gerar_plano_tratamento/<int:odontograma_id>/', views.gerar_plano_tratamento, name="gerar_plano_tratamento"),
    path('ordem_plano_tratamento/<int:item_plano_tratamento>/<int:tipo>/', views.ordem_plano_tratamento, name="ordem_plano_tratamento"),
    path('resolver_exame_periodontal/<int:exame_id>/', views.resolver_exame_periodontal, name="resolver_exame_periodontal"),
    path('historico_exame_estomatologico/<int:atendimento_id>/', views.historico_exame_estomatologico, name="historico_exame_estomatologico"),
    path('alterar_tipo_consulta/<int:atendimento_id>/', views.alterar_tipo_consulta, name="alterar_tipo_consulta"),
    path('relatorios_atendimentos_odontologicos/', views.relatorios_atendimentos_odontologicos, name="relatorios_atendimentos_odontologicos"),
    path('excluir_exame_periodontal/<int:exame_id>/', views.excluir_exame_periodontal, name="excluir_exame_periodontal"),
    path('excluir_procedimento_odontologico/<int:procedimento_id>/', views.excluir_procedimento_odontologico, name="excluir_procedimento_odontologico"),
    path('obs_registrar_execucao/<int:plano_tratamento_id>/', views.obs_registrar_execucao, name="obs_registrar_execucao"),
    path('encaminhar_enfermagem_odonto/<int:atendimento_id>/', views.encaminhar_enfermagem_odonto, name="encaminhar_enfermagem_odonto"),
    path('registrar_intervencao_odonto/<int:atendimento_id>/<int:atendimento_origem_id>/', views.registrar_intervencao_odonto, name="registrar_intervencao_odonto"),
    # Cartão Vacinal
    path('adicionar_vacina/<int:prontuario_id>/', views.adicionar_vacina, name="adicionar_vacina"),
    path('registrar_vacinacao/<int:vacinacao_id>/', views.registrar_vacinacao, name="registrar_vacinacao"),
    path('registrar_previsao/<int:vacinacao_id>/', views.registrar_previsao, name="registrar_previsao"),
    path('deletar_vacina/<int:prontuario_id>/<int:vacina_id>/', views.deletar_vacina, name="deletar_vacina"),
    path('adicionar_dose/<int:prontuario_id>/<int:vacina_id>/', views.adicionar_dose, name="adicionar_dose"),
    path('remover_dose/<int:registro_id>/', views.remover_dose, name="remover_dose"),
    path('remover_previsao/<int:vacinacao_id>/', views.remover_previsao, name="remover_previsao"),
    path('adicionar_cartao_vacinal/<int:vinculo_id>/', views.adicionar_cartao_vacinal, name="adicionar_cartao_vacinal"),
    path('cartao_vacinal/', views.cartao_vacinal, name="cartao_vacinal"),
    path('adicionar_cartao_vacinal_aluno/', views.adicionar_cartao_vacinal_aluno, name="adicionar_cartao_vacinal_aluno"),
    path('historico_cartao_vacinal/<int:vinculo_id>/', views.historico_cartao_vacinal, name="historico_cartao_vacinal"),
    # Relatórios
    path('estatistica_geral_atendimento/', views.estatistica_geral_atendimento, name="estatistica_geral_atendimento"),
    path('indicadores/', views.indicadores, name="indicadores"),
    path('graficos_antropometria/', views.graficos_antropometria, name="graficos_antropometria"),
    path('graficos_acuidade_visual/', views.graficos_acuidade_visual, name="graficos_acuidade_visual"),
    path('graficos_saude_doenca/', views.graficos_saude_doenca, name="graficos_saude_doenca"),
    path('graficos_habitos_vida/', views.graficos_habitos_vida, name="graficos_habitos_vida"),
    path('graficos_desenvolvimento_pessoal/', views.graficos_desenvolvimento_pessoal, name="graficos_desenvolvimento_pessoal"),
    path('graficos_exame_fisico/', views.graficos_exame_fisico, name="graficos_exame_fisico"),
    path('graficos_percepcao_saude_bucal/', views.graficos_percepcao_saude_bucal, name="graficos_percepcao_saude_bucal"),
    path('graficos_vacinas/', views.graficos_vacinas, name="graficos_vacinas"),
    path('relatorio_cartoes_vacinais/', views.relatorio_cartoes_vacinais, name="relatorio_cartoes_vacinais"),
    path('relatorio_atendimento_odontologia/', views.relatorio_atendimento_odontologia, name="relatorio_atendimento_odontologia"),
    path('relatorio_atendimento_medico_enfermagem/', views.relatorio_atendimento_medico_enfermagem, name="relatorio_atendimento_medico_enfermagem"),
    path('relatorio_atendimento_psicologia/', views.relatorio_atendimento_psicologia, name="relatorio_atendimento_psicologia"),
    # Exames Complementares
    path('adicionar_exame_laboratorial/<int:prontuario_id>/', views.adicionar_exame_laboratorial, name="adicionar_exame_laboratorial"),
    path('adicionar_exame_imagem/<int:prontuario_id>/', views.adicionar_exame_imagem, name="adicionar_exame_imagem"),
    path('ver_exame_laboratorial/<int:exame_id>/', views.ver_exame_laboratorial, name="ver_exame_laboratorial"),
    path('editar_exame_laboratorial/<int:exame_id>/', views.editar_exame_laboratorial, name="editar_exame_laboratorial"),
    path('ver_exame_imagem/<int:exame_id>/', views.ver_exame_imagem, name="ver_exame_imagem"),
    path('editar_exame_imagem/<int:exame_id>/', views.editar_exame_imagem, name="editar_exame_imagem"),
    path('excluir_exame_laboratorial/<int:exame_id>/', views.excluir_exame_laboratorial, name="excluir_exame_laboratorial"),
    path('excluir_exame_imagem/<int:exame_id>/', views.excluir_exame_imagem, name="excluir_exame_imagem"),
    path('exame_laboratorial_valores_referencia/', views.exame_laboratorial_valores_referencia, name="exame_laboratorial_valores_referencia"),
    path('adicionar_valores_exame_laboratorial/<int:exame_laboratorial_id>/', views.adicionar_valores_exame_laboratorial, name="adicionar_valores_exame_laboratorial"),
    # Outros
    path('historico_ficha/<int:atendimento_id>/<int:ficha>/', views.historico_ficha, name="historico_ficha"),
    path('cadastrar_pessoa_externa/', views.cadastrar_pessoa_externa, name="cadastrar_pessoa_externa"),
    path('atividade_em_grupo/<int:atividade_id>/', views.atividade_em_grupo, name="atividade_em_grupo"),
    path('cancelar_atividade_grupo/<int:atividade_id>/', views.cancelar_atividade_grupo, name="cancelar_atividade_grupo"),
    path('adicionar_anotacao_interdisciplinar/<int:prontuario_id>/', views.adicionar_anotacao_interdisciplinar, name="adicionar_anotacao_interdisciplinar"),
    path('editar_cartao_sus/<int:aluno_id>/', views.editar_cartao_sus, name="editar_cartao_sus"),
    path('adicionar_acao_educativa/<int:meta_id>/', views.adicionar_acao_educativa, name="adicionar_acao_educativa"),
    path('visualizar_acoes_educativas/<int:meta_id>/', views.visualizar_acoes_educativas, name="visualizar_acoes_educativas"),
    path('registrar_execucao_acao_educativa/<int:atividadegrupo_id>/', views.registrar_execucao_acao_educativa, name="registrar_execucao_acao_educativa"),
    path('visualizar_acao_educativa/<int:atividadegrupo_id>/', views.visualizar_acao_educativa, name="visualizar_acao_educativa"),
    path('visualizar_meta_acao_educativa/<int:meta_id>/', views.visualizar_meta_acao_educativa, name="visualizar_meta_acao_educativa"),
    path('adicionar_acao_educativa_sem_meta/', views.adicionar_acao_educativa_sem_meta, name="adicionar_acao_educativa_sem_meta"),
    path('cancelar_acao_educativa/<int:atividadegrupo_id>/', views.cancelar_acao_educativa, name="cancelar_acao_educativa"),
    path('lista_alunos/', views.lista_alunos, name="lista_alunos"),
    path('adicionar_documento_prontuario/<int:vinculo_id>/', views.adicionar_documento_prontuario, name="adicionar_documento_prontuario"),
    path('preencher_documento_prontuario/<int:vinculo_id>/<int:tipo>/', views.preencher_documento_prontuario, name="preencher_documento_prontuario"),
    path('imprimir_documento_prontuario/<int:documento_id>/', views.imprimir_documento_prontuario, name="imprimir_documento_prontuario"),
    path('previsualizar_documento_prontuario/', views.previsualizar_documento_prontuario, name="previsualizar_documento_prontuario"),
    path('excluir_documento_prontuario/<int:documento_id>/', views.excluir_documento_prontuario, name="excluir_documento_prontuario"),
    # PSICOLOGIA
    path('atendimento_psicologico/<int:atendimento_id>/', views.atendimento_psicologico, name="atendimento_psicologico"),
    path('adicionar_motivo_psicologia/<int:atendimento_id>/', views.adicionar_motivo_psicologia, name="adicionar_motivo_psicologia"),
    path('adicionar_anamnese_psicologica/<int:vinculo_id>/', views.adicionar_anamnese_psicologica, name="adicionar_anamnese_psicologica"),
    path('registrar_hora_atendimento/<int:atendimento_id>/', views.registrar_hora_atendimento, name="registrar_hora_atendimento"),
    path('adicionar_anexo_psicologia/<int:atendimento_id>/', views.adicionar_anexo_psicologia, name="adicionar_anexo_psicologia"),
    path('editar_anexo_psicologia/<int:anexo_id>/', views.editar_anexo_psicologia, name="editar_anexo_psicologia"),
    path('remover_anexo_psicologia/<int:anexo_id>/', views.remover_anexo_psicologia, name="remover_anexo_psicologia"),
    # NUTRICAO
    path('atendimento_nutricional/<int:atendimento_id>/', views.atendimento_nutricional, name="atendimento_nutricional"),
    path('adicionar_motivo_nutricao/<int:atendimento_id>/', views.adicionar_motivo_nutricao, name="adicionar_motivo_nutricao"),
    path('adicionar_avaliacao_gastrointestinal/<int:atendimento_id>/', views.adicionar_avaliacao_gastrointestinal, name="adicionar_avaliacao_gastrointestinal"),
    path('adicionar_dados_alimentacao/<int:atendimento_id>/', views.adicionar_dados_alimentacao, name="adicionar_dados_alimentacao"),
    path('adicionar_restricao_alimentar/<int:atendimento_id>/', views.adicionar_restricao_alimentar, name="adicionar_restricao_alimentar"),
    path('adicionar_consumo_nutricao/<int:atendimento_id>/', views.adicionar_consumo_nutricao, name="adicionar_consumo_nutricao"),
    path('adicionar_diagnostico_nutricional/<int:atendimento_id>/', views.adicionar_diagnostico_nutricional, name="adicionar_diagnostico_nutricional"),
    path('adicionar_categoria_trabalho/<int:atendimento_id>/', views.adicionar_categoria_trabalho, name="adicionar_categoria_trabalho"),
    path('adicionar_conduta_nutricao/<int:atendimento_id>/', views.adicionar_conduta_nutricao, name="adicionar_conduta_nutricao"),
    path('remover_conduta_nutricao/<int:atendimentonutricao_id>/', views.remover_conduta_nutricao, name="remover_conduta_nutricao"),
    path('imprimir_plano_alimentar/<int:plano_id>/', views.imprimir_plano_alimentar, name="imprimir_plano_alimentar"),
    path('remover_plano_alimentar/<int:plano_id>/', views.remover_plano_alimentar, name="remover_plano_alimentar"),
    path('remover_receita/<int:atendimentonutricao_id>/<int:receita_id>/', views.remover_receita, name="remover_receita"),
    path('remover_consumo/<int:consumo_id>/', views.remover_consumo, name="remover_consumo"),
    path('editar_consumo/<int:consumo_id>/', views.editar_consumo, name="editar_consumo"),
    path('adicionar_plano_alimentar/<int:atendimento_id>/', views.adicionar_plano_alimentar, name="adicionar_plano_alimentar"),
    path('editar_plano_alimentar/<int:plano_id>/', views.editar_plano_alimentar, name="editar_plano_alimentar"),
    path('adicionar_marcadores_consumo_alimentar/<int:atendimento_id>/', views.adicionar_marcadores_consumo_alimentar, name="adicionar_marcadores_consumo_alimentar"),
    path('excluir_marcadores_consumo_alimentar/<int:atendimento_id>/', views.excluir_marcadores_consumo_alimentar, name="excluir_marcadores_consumo_alimentar"),
    # FISIOTERAPIA
    path('atendimento_fisioterapia/<int:atendimento_id>/', views.atendimento_fisioterapia, name="atendimento_fisioterapia"),
    path('adicionar_anamnese_fisioterapia/<int:atendimento_id>/', views.adicionar_anamnese_fisioterapia, name="adicionar_anamnese_fisioterapia"),
    path('adicionar_hipotese_fisioterapia/<int:atendimento_id>/', views.adicionar_hipotese_fisioterapia, name="adicionar_hipotese_fisioterapia"),
    path('adicionar_conduta_fisioterapia/<int:atendimento_id>/', views.adicionar_conduta_fisioterapia, name="adicionar_conduta_fisioterapia"),
    path('adicionar_intervencao_fisioterapia/<int:atendimento_id>/', views.adicionar_intervencao_fisioterapia, name="adicionar_intervencao_fisioterapia"),
    path('adicionar_retorno_fisioterapia/<int:atendimento_id>/', views.adicionar_retorno_fisioterapia, name="adicionar_retorno_fisioterapia"),
    # MULTIDISCIPLINARES
    path('atendimento_multidisciplinar/<int:atendimento_id>/', views.atendimento_multidisciplinar, name="atendimento_multidisciplinar"),
    path('adicionar_procedimento_multidisciplinar/<int:atendimento_id>/', views.adicionar_procedimento_multidisciplinar, name="adicionar_procedimento_multidisciplinar"),
    # AGENDAMENTO
    path('agenda_atendimentos/', views.agenda_atendimentos, name="agenda_atendimentos"),
    path('adicionar_horario_atendimento_saude/', views.adicionar_horario_atendimento_saude, name="adicionar_horario_atendimento_saude"),
    path('reservar_horario_atendimento/<int:horario_id>/', views.reservar_horario_atendimento, name="reservar_horario_atendimento"),
    path('cancelar_horario_atendimento/<int:horario_id>/', views.cancelar_horario_atendimento, name="cancelar_horario_atendimento"),
    path('bloquear_aluno_atendimento/<int:horario_id>/', views.bloquear_aluno_atendimento, name="bloquear_aluno_atendimento"),
    path('desbloquear_aluno_atendimento/<int:vinculo_paciente_id>/', views.desbloquear_aluno_atendimento, name="desbloquear_aluno_atendimento"),
    path('cancelar_horarios_atendimentos/', views.cancelar_horarios_atendimentos, name="cancelar_horarios_atendimentos"),
    path('informar_motivo_cancelamento_horario/', views.informar_motivo_cancelamento_horario, name="informar_motivo_cancelamento_horario"),
    path('ver_calendario_agendamento/', views.ver_calendario_agendamento, name="ver_calendario_agendamento"),
    # COVID
    path('passaporte_vacinacao_covid/', views.passaporte_vacinacao_covid, name="passaporte_vacinacao_covid"),
    path('deferir_passaporte_vacinal/<int:declaracao_id>/', views.deferir_passaporte_vacinal, name="deferir_passaporte_vacinal"),
    path('indeferir_passaporte_vacinal/<int:declaracao_id>/', views.indeferir_passaporte_vacinal, name="indeferir_passaporte_vacinal"),
    path('relatorio_passaporte_vacinal/', views.relatorio_passaporte_vacinal, name="relatorio_passaporte_vacinal"),
    path('relatorio_vacinacao_covid/', views.relatorio_vacinacao_covid, name="relatorio_vacinacao_covid"),
    path('importar_dados_vacinacao/', views.importar_dados_vacinacao, name="importar_dados_vacinacao"),
    path('ver_historico_validacao_passaporte/<int:passaporte_id>/', views.ver_historico_validacao_passaporte, name="ver_historico_validacao_passaporte"),
    path('cadastrar_resultado_teste/<int:passaporte_id>/', views.cadastrar_resultado_teste, name="cadastrar_resultado_teste"),
    path('resultados_testes_covid/<int:passaporte_id>/', views.resultados_testes_covid, name="resultados_testes_covid"),
    path('deferir_teste_covid/<int:resultado_id>/', views.deferir_teste_covid, name="deferir_teste_covid"),
    path('indeferir_teste_covid/<int:resultado_id>/', views.indeferir_teste_covid, name="indeferir_teste_covid"),
    path('relatorio_passaporte_vacinal_chefia/', views.relatorio_passaporte_vacinal_chefia, name="relatorio_passaporte_vacinal_chefia"),
    path('cadastrar_cartao_vacinal_covid/', views.cadastrar_cartao_vacinal_covid, name="cadastrar_cartao_vacinal_covid"),
    path('notificar_caso_covid/', views.notificar_caso_covid, name="notificar_caso_covid"),
    path('monitorar_notificacao_covid/<int:notificacao_id>/', views.monitorar_notificacao_covid, name="monitorar_notificacao_covid"),
    path('ver_monitoramentos_covid/<int:notificacao_id>/', views.ver_monitoramentos_covid, name="ver_monitoramentos_covid"),
    path('relatorio_notificacao_covid/', views.relatorio_notificacao_covid, name="relatorio_notificacao_covid"),
    path('verificacao_passaporte_vacinal/', views.verificacao_passaporte_vacinal, name="verificacao_passaporte_vacinal"),
]