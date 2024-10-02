from django.urls import path

from residencia import views

urlpatterns = [
    path('efetuarmatricula/', views.efetuarmatricula, name='efetuarmatricula'),
    path('residente/<str:matricula>/', views.residente, name='residente'),
    path('atualizar_email_secundario/<int:residente_pk>/', views.atualizar_email),
    path('atualizar_dados_pessoais/<int:residente_pk>/', views.atualizar_dados_pessoais),
    path('atualizar_meus_dados_pessoais/<str:matricula>/', views.atualizar_meus_dados_pessoais),
    path('atualizar_foto/<int:residente_pk>/', views.atualizar_foto),
    path('adicionar_observacao/<int:residente_pk>/', views.adicionar_observacao),
    path('editar_observacao/<int:observacao_pk>/', views.editar_observacao),
    path('meus_dados/', views.meus_dados_academicos),
    path('solicitar_matricula_residente/', views.solicitar_matricula_residente),
    path('analisar_solicitresidente/<int:solicitresidente_pk>/', views.analisar_solicitresidente),

    # Estágio Eletivo
    path('analisar_soliciteletivo/<int:solicitresidente_pk>/', views.analisar_soliciteletivo),
    path('solicitacoes_eletivo/', views.minhas_solicitacoes_eletivo, name="minhas_solicitacoes_eletivo_residencia"),
    path('solicitacao_eletivo/<int:pk>/', views.visualizar_solicitacao_eletivo),
    path('solicitar_eletivo/', views.solicitar_eletivo, name="solicitar_eletivo_residencia"),
    path('estagios_eletivos/', views.meus_estagios_eletivos, name="meus_estagios_eletivos_residencia"),
    path('estagio_eletivo/<int:pk>/', views.visualizar_estagio_eletivo),
    path('adicionar_anexo_eletivo/<int:pk>/<int:tipo>/', views.adicionar_anexo_eletivo),

    # Secretário(a) Residência
    path('secretarios_residencia/', views.secretarios_residencia, name="secretarios_residencia"),
    path('cadastrar_secretario_residencia/', views.cadastrar_secretario_residencia, name="cadastrar_secretario_residencia"),
    path('editar_secretario_residencia/<int:empregado_id>/', views.editar_secretario_residencia, name="editar_secretario_residencia"),

    # Preceptor(a)
    path('preceptores/', views.preceptores, name="preceptores"),
    path('cadastrar_preceptor/', views.cadastrar_preceptor,
         name="cadastrar_preceptor"),
    path('editar_preceptor/<int:empregado_id>/', views.editar_preceptor,
         name="editar_preceptor"),

    # Apoiador Pedagógico Residência
    path('apoiadores_pedagogicos_residencia/', views.apoiadores_pedagogicos_residencia, name="apoiadores_pedagogicos_residencia"),
    path('cadastrar_apoiador_pedagogico_residencia/', views.cadastrar_apoiador_pedagogico_residencia),
    path('cadastrar_apoiador_pedagogico_residencia/<int:pessoafisica_id>/', views.cadastrar_apoiador_pedagogico_residencia),
    path('editar_apoiador_pedagogico_residencia/<int:bolsista_id>/', views.editar_apoiador_pedagogico_residencia,
         name="editar_apoiador_pedagogico_residencia"),

    # Coordenador(a) Residência
    path('coordenadores_residencia/', views.coordenadores_residencia, name="coordenadores_residencia"),
    path('cadastrar_coordenador_residencia/', views.cadastrar_coordenador_residencia, name="cadastrar_coordenador_residencia"),
    path('editar_coordenador_residencia/<int:empregado_id>/', views.editar_coordenador_residencia, name="editar_coordenador_residencia"),

    #Matriz
    path('matriz/<int:pk>/', views.matriz),
    path('vincular_componente/<int:matriz_pk>/', views.vincular_componente),
    path('vincular_componente/<int:matriz_pk>/<int:componente_pk>/', views.vincular_componente),

    path('matriz_pdf/<int:pk>/', views.matriz_pdf),
    path('grade_curricular/<int:matriz_pk>/', views.grade_curricular),
    path('replicar_matriz/<int:pk>/', views.replicar_matriz),

    path('cursoresidencia/<int:pk>/', views.cursoresidencia),
    path('definir_coordenador_residencia/<int:pk>/', views.definir_coordenador_residencia),
    path('adicionar_matriz_curso/<int:curso_residencia_pk>/', views.adicionar_matriz_curso),
    path('adicionar_matriz_curso/<int:curso_residencia_pk>/<int:matriz_curso_pk>/', views.adicionar_matriz_curso),

    path('estruturacurso/<int:estrutura_curso_pk>/', views.visualizar_estrutura_curso),

    path('gerar_turmas/', views.gerar_turmas),
    path('turma/<int:pk>/', views.turma),
    path('adicionar_residente_turma/<int:pk>/', views.adicionar_residente_turma),

    path('adicionar_projeto_final_residente/<int:residente_pk>/', views.adicionar_projeto_final_residente),
    path('adicionar_projeto_final_residente/<int:residente_pk>/<int:projetofinal_residente_pk>/', views.adicionar_projeto_final_residente),
    path('lancar_resultado_projeto_final_residente/<int:projetofinal_residente_pk>/', views.lancar_resultado_projeto_final_residente),
    path('upload_documento_projeto_final_residente/<int:projetofinal_residente_pk>/', views.upload_documento_projeto_final_residente),
    path('ata_projeto_final_residente_pdf/<int:projetofinalresidente_pk>/', views.ata_projeto_final_residente_pdf),
    path('declaracao_participacao_projeto_final_residente/<int:projetofinalresidente_pk>/', views.declaracao_participacao_projeto_final_residente),
    path('declaracao_participacao_projeto_final_residente_pdf/<int:pk>/<str:participante>/', views.declaracao_participacao_projeto_final_residente_pdf),
    path('visualizar_projeto_final_residente/<int:projetofinal_residente_pk>/', views.visualizar_projetofinal_residente),

    path('assinar_ata_eletronica_residente/<int:pk>/', views.assinar_ata_eletronica_residencia),
    path('visualizar_ata_eletronica_residente/<int:pk>/', views.visualizar_ata_eletronica_residente),
    path('ata_eletronica_projeto_final_residente_pdf/<int:pk>/', views.ata_eletronica_projeto_final_residente_pdf),

    path('diario/<int:pk>/', views.diario),
    path('adicionar_observacaodiario/<int:diario_pk>/', views.adicionar_observacaodiario),
    path('editar_observacaodiario/<int:observacao_pk>/', views.editar_observacaodiario),
    path('adicionar_preceptor_diario/<int:diario_pk>/', views.adicionar_preceptor_diario),
    path('adicionar_preceptor_diario/<int:diario_pk>/<int:preceptordiario_pk>/', views.adicionar_preceptor_diario),
    path('diario_pdf/<int:pk>/<int:etapa>/', views.diario_pdf),
    path('adicionar_residentes_diario/<int:diario_pk>/', views.adicionar_residentes_diario),
    path('meus_diarios/', views.meus_diarios),
    path('meus_diarios/<str:diarios>/', views.meus_diarios),
    path('meu_diario/<int:diario_pk>/<int:etapa>/', views.meu_diario),
    path('confirmar_frequencia_residente/<int:frequencia_pk>/', views.confirmar_frequencia_residente),
    path('adicionar_frequencia_residente/<int:residente_pk>/', views.adicionar_frequencia_residente),
    path('upload_documento_frequencia_residente/<int:residente_pk>/', views.upload_documento_frequencia_residente),

    #Solicitações
    path('solicitacaousuario/<int:pk>/', views.solicitacaousuario),
    path('solicitar_desligamento/', views.solicitar_desligamento),
    path('solicitar_diplomas/', views.solicitar_diplomas),
    path('solicitar_ferias/', views.solicitar_ferias),
    path('solicitar_licencas/', views.solicitar_licencas),
    path('solicitar_congressos/', views.solicitar_congressos),

    path('atender_solicitacaousuario/<str:pks>/', views.atender_solicitacaousuario),
    path('rejeitar_solicitacao/<str:pks>/', views.rejeitar_solicitacao),

    #Relatorios
    path('relatorio_corpo_pedagogico/', views.relatorio_corpo_pedagogico),
    path('estatistica/', views.estatistica),
    path('estatistica_eletivo/', views.estatistica_eletivo),


    path('registrar_nota_ajax/<int:id_nota_avaliacao>/', views.registrar_nota_ajax),
    path('registrar_nota_ajax/<int:id_nota_avaliacao>/<int:nota>/', views.registrar_nota_ajax),

    path('declaracaomatricularesidente_pdf/<int:pk>/', views.declaracaomatricularesidente_pdf),
    path('declaracao_orientacao_tcr/<int:pk>/', views.declaracao_orientacao_tcr),


    path('unidadeaprendizagemturma/<int:pk>/', views.unidadeaprendizagemturma),

    path('matricular_avulso_unidadeaprendizagemturma/<int:unidadeaprendizagemturma_pk>/', views.matricular_avulso_unidadeaprendizagemturma),

    path('registrar_nota_unidade_ajax/<int:id_nota_avaliacao>/', views.registrar_nota_unidade_ajax),
    path('registrar_nota_unidade_ajax/<int:id_nota_avaliacao>/<int:nota>/', views.registrar_nota_unidade_ajax),

    path('calendarioacademico/<int:pk>/', views.calendarioacademico),
    path('transferir_posse_unidadeaprendizagemturma/<int:unidadeaprendizagemturma_pk>/<int:etapa>/<int:destino>/', views.transferir_posse_unidadeaprendizagemturma),


]