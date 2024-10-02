from django.urls import path
from ppe import views

urlpatterns = [
    path('efetuarmatriculatrabalhadoreducando/', views.efetuarmatriculatrabalhadoreducando, name='efetuarmatriculatrabalhadoreducando'),
    path('trabalhadoreducando/<str:matricula>/', views.trabalhadoreducando, name='trabalhadoreducando'),
    path('atualizar_email_secundario/<int:trabalhadoreducando_pk>/', views.atualizar_email),
    path('atualizar_dados_pessoais/<int:trabalhadoreducando_pk>/', views.atualizar_dados_pessoais),
    path('atualizar_meus_dados_pessoais/<str:matricula>/', views.atualizar_meus_dados_pessoais),
    path('atualizar_foto/<int:trabalhadoreducando_pk>/', views.atualizar_foto),
    path('adicionar_observacao/<int:trabalhadoreducando_pk>/', views.adicionar_observacao),
    path('editar_observacao/<int:observacao_pk>/', views.editar_observacao),
    path('meus_dados/', views.meus_dados_academicos),
    path('alterar_trabalhador_setor_historico/<int:trabalhadoreducando_pk>/', views.alterar_trabalhador_setor_historico),

    # Coordenadores(as) PPE
    path('coordenadores_ppe/', views.coordenadores_ppe, name="coordenadores_ppe"),
    path('cadastrar_coordenador_ppe/', views.cadastrar_coordenador_ppe, name="cadastrar_coordenador_ppe"),
    path('editar_coordenador_ppe/<int:empregado_id>/', views.editar_coordenador_ppe, name="editar_coordenador_ppe"),

    # Supervidores(as) Campo PPE
    path('supervisores_campo_ppe/', views.supervisores_campo_ppe, name="supervisores_campo_ppe"),
    path('cadastrar_supervisor_campo_ppe/', views.cadastrar_supervisor_campo_ppe, name="cadastrar_supervisor_campo_ppe"),
    path('editar_supervisor_campo_ppe/<int:empregado_id>/', views.editar_supervisor_campo_ppe, name="editar_supervisor_campo_ppe"),

    # Chefia imediata
    path('nova_chefia_imediata', views.cadastrar_chefia_imediata),
    path('nova_chefia_imediata/<int:pessoafisica_id>/', views.cadastrar_chefia_imediata),
    path('chefia_imediata/<int:pk>/', views.chefia_imediata),

    # Gestor de Campo PPE
    path('gestores_ppe/', views.gestores_ppe, name="gestores_ppe"),
    path('cadastrar_gestor_ppe/', views.cadastrar_gestor_ppe, name="cadastrar_gestor_ppe"),
    path('editar_gestor_ppe/<int:empregado_id>/', views.editar_gestor_ppe, name="editar_gestor_ppe"),

    # Apoiador Administrativo PPE
    path('apoiadores_administrativos_ppe/', views.apoiadores_administrativos_ppe, name="apoiadores_administrativos_ppe"),
    path('cadastrar_apoiador_administrativo_ppe/', views.cadastrar_apoiador_administrativo_ppe, name="cadastrar_apoiador_administrativo_ppe"),
    path('editar_apoiador_administrativo_ppe/<int:empregado_id>/', views.editar_apoiador_administrativo_ppe, name="editar_apoiador_administrativo_ppe"),

    # Supervisor Pedagógico PPE
    path('supervisores_pedagogicos_ppe/', views.supervisores_pedagogicos_ppe, name="supervisores_pedagogicos_ppe"),
    path('cadastrar_supervisor_pedagogico_ppe/', views.cadastrar_supervisor_pedagogico_ppe, name="cadastrar_supervisor_pedagogico_ppe"),
    path('editar_supervisor_pedagogico_ppe/<int:empregado_id>/', views.editar_supervisor_pedagogico_ppe, name="editar_supervisor_pedagogico_ppe"),

    # Supervisor Psicossocial PPE
    path('supervisores_psicossociais_ppe/', views.supervisores_psicossociais_ppe, name="supervisores_psicossociais_ppe"),
    path('cadastrar_supervisor_psicossocial_ppe/', views.cadastrar_supervisor_psicossocial_ppe, name="cadastrar_supervisor_psicossocial_ppe"),
    path('editar_supervisor_psicossocial_ppe/<int:empregado_id>/', views.editar_supervisor_psicossocial_ppe, name="editar_supervisor_psicossocial_ppe"),

    # Apoiador Pedagógico PPE
    path('apoiadores_pedagogicos_ppe/', views.apoiadores_pedagogicos_ppe, name="apoiadores_pedagogicos_ppe"),
    path('cadastrar_apoiador_pedagogico_ppe/', views.cadastrar_apoiador_pedagogico_ppe),
    path('cadastrar_apoiador_pedagogico_ppe/<int:pessoafisica_id>/', views.cadastrar_apoiador_pedagogico_ppe),

    # Tutor PPE
    path('tutores_ppe/', views.tutores_ppe, name="tutores_ppe"),
    path('cadastrar_tutor_ppe/', views.cadastrar_tutor_ppe),
    path('cadastrar_tutor_ppe/<int:pessoafisica_id>/', views.cadastrar_tutor_ppe),

    # Visualizar Estrutura Curso
    path('estruturacurso/<int:estrutura_curso_pk>/', views.visualizar_estrutura_curso),

    path('curso/<int:pk>/', views.curso),
    path('formacaoppe/<int:pk>/', views.formacaoppe),
    path('vincular_curso_ppe/<int:formacaoppe_pk>/', views.vincular_curso_ppe),
    path('vincular_curso_ppe/<int:formacaoppe_pk>/<int:curso_pk>/', views.vincular_curso_ppe),

    path('replicar_formacaoppe/<int:formacaoppe_pk>/', views.replicar_formacaoppe),


    path('gerar_turmas/', views.gerar_turmas),
    path('turma/<int:pk>/', views.turma),
    path('adicionar_tutor_turma/<int:turma_pk>/', views.adicionar_tutor_turma),
    path('adicionar_tutor_turma/<int:turma_pk>/<int:tutorturma_pk>/', views.adicionar_tutor_turma),
    path('adicionar_apoiador_turma/<int:turma_pk>/', views.adicionar_apoiador_turma),
    path('adicionar_apoiador_turma/<int:turma_pk>/<int:apoiadorturma_pk>/', views.adicionar_apoiador_turma),
    path('alterar_data_curso_turma/<int:curso_turma_pk>/', views.alterar_data_curso_turma),
    path('calendario_turma/<int:pk>/', views.calendario_turma),

    #FES-49
    path('anamnese/', views.anamnese),
    path('matricular_trabalhador_educando_turma/<int:trabalhador_educando_pk>/', views.matricular_trabalhador_educando_turma),
    path('adicionar_trabalhadores_educando_turma/<int:pk>/', views.adicionar_trabalhadores_educando_turma),
    path('matricular_trabalhador_educando_avulso_curso_turma/<int:curso_turma_pk>/', views.matricular_trabalhador_educando_avulso_curso_turma),

    path('curso_turma/<int:pk>/', views.curso_turma),
    path('configuracao_avaliacao/<int:pk>/', views.configuracao_avaliacao),
    path('transferir_posse_curso_turma/<int:curso_turma_pk>/<int:etapa>/<int:destino>/', views.transferir_posse_curso_turma),
    path('registrar_nota_ajax/<int:id_nota_avaliacao>/', views.registrar_nota_ajax),
    path('registrar_nota_ajax/<int:id_nota_avaliacao>/<int:nota>/', views.registrar_nota_ajax),
    path('detalhar_matricula_curso_turma_boletim/<int:trabalhador_educando_pk>/<int:matricula_curso_turma_pk>/', views.detalhar_matricula_curso_turma_boletim),

    path('minhas_turmas/', views.minhas_turmas),
    path('minhas_turmas/<str:turmas>/', views.minhas_turmas),
    path('meu_curso_turma/<int:curso_turma_pk>/<int:etapa>/<int:polo_pk>/', views.meu_curso_turma),
    path('meu_curso_turma/<int:curso_turma_pk>/<int:etapa>/', views.meu_curso_turma),

    path('relatorio_ppe/', views.relatorio_ppe),
    path('salvar_relatorio_ppe/<int:tipo>/<str:query_string>/', views.salvar_relatorio_ppe),
    # path('entregar_etapa/<int:curso_turma>/<int:etapa>/', views.entregar_etapa),

    path('relatorio_aprovados_ppe/', views.relatorio_aprovados_ppe),
    path('registrar_chamada/<int:curso_turma_pk>/', views.registrar_chamada),
    path('registrar_chamada/<int:curso_turma_pk>/<int:etapa>/', views.registrar_chamada),
    path('registrar_chamada/<int:curso_turma_pk>/<int:etapa>/<int:matricula_diario_pk>/', views.registrar_chamada),

    path('log_curso_turma/<int:pk>/', views.log_curso_turma),
    path('log/<int:pk>/', views.log),

    path('solicitacaousuario/<int:pk>/', views.solicitacaousuario),
    path('solicitar_atendimentopsicossocial/', views.solicitar_atendimentopsicossocial),
    path('solicitar_continuidadeaperfeicoamentoprofissional/', views.solicitar_continuidadeaperfeicoamentoprofissional),
    path('solicitar_ampliacaoprazocurso/', views.solicitar_ampliacaoprazocurso),
    path('solicitar_realocacao/', views.solicitar_realocacao),
    path('solicitar_visitatecnicaunidade/', views.solicitar_visitatecnicaunidade),
    path('solicitar_desligamento/', views.solicitar_desligamento),

    path('atender_solicitacaousuario/<str:pks>/', views.atender_solicitacaousuario),
    path('rejeitar_solicitacao/<str:pks>/', views.rejeitar_solicitacao),

    #Relatórios
    path('relatorio_faltas/', views.relatorio_faltas),

    path('mapa_notas_ppe/<int:pk>/', views.mapa_notas_ppe),
    path('avaliacao_trabalhador_educando/<int:trabalhador_educando_id>/<int:tipo_avaliacao_id>/', views.avaliacao_trabalhador_educando),
    path('avaliacao_trabalhador_educando_confirmacao/<int:avaliacao_id>/', views.avaliacao_trabalhador_educando_confirmacao),
    path('gerar_pdf_trabalhador_educando_resumo/<int:avaliacao_id>/', views.gerar_pdf_trabalhador_educando_resumo),
    path('avaliacoes_chefia/', views.avaliacoes_chefia),


    path('setor/<int:pk>/', views.setor),
    path('declaracaomatriculappe_pdf/<int:pk>/', views.declaracaomatriculappe_pdf),
    path('alterar_nome_breve_curso_moodle/<int:pk_curso_turma>/', views.alterar_nome_breve_curso_moodle),




    # FES-78
    path('certconclusaoporcursoppe/<int:pk>/', views.certconclusaoporcursoppe, name='certconclusaoporcursoppe'),
    path('certconclusaoporcursoppe_pdf/<int:pk>/', views.certconclusaoporcursoppe_pdf, name='certconclusaoporcursoppe_pdf'),

    # FES-79
    path('certtrezentashorasppe_pdf/<int:pk>/', views.certtrezentashorasppe_pdf),

]
