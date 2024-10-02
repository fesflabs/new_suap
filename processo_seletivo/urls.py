from django.urls import path

from processo_seletivo import views

urlpatterns = [
    path('importar_edital_xml/<int:pk>/', views.importar_edital_xml),
    path('importar_edital/', views.importar_edital),
    path('edital/<int:pk>/', views.edital),
    path('oferta_vaga_curso_ajax/<int:pk>/', views.oferta_vaga_curso_ajax, name='oferta_vaga_curso_ajax'),
    path('edital/<int:pk>/ausentar_candidatos/', views.edital_ausentar_candidatos, name="ps_edital_ausentar"),
    path('edital/<int:edital_pk>/liberacao/', views.edital_periodo_liberacao, name="ps_edital_liberacao_add"),
    path('edital/<int:edital_pk>/liberacao/<int:pk>/change/', views.edital_periodo_liberacao, name="ps_edital_liberacao_change"),
    path('edital/historico_edital_periodo_liberacao/<int:edital_liberacao_periodo_pk>/', views.historico_edital_periodo_liberacao, name="ps_historico_liberacao_periodo_edital"),
    path('oferta_vaga/<int:pk>/', views.oferta_vaga),
    path('classificados/<int:pk>/<str:polo>/', views.classificados),
    path('classificados/<int:pk>/', views.classificados),
    path('candidato/<int:pk>/', views.candidato),
    path('visualizar_vagas/<int:pk>/<int:tipo>/', views.visualizar_vagas),
    path('matricular_alunos_proitec/<int:pk>/<int:ano>/<int:periodo>/', views.matricular_alunos_proitec),
    path('definir_configuracao_migracao_vaga/<int:pk>/', views.definir_configuracao_migracao_vaga),
    path('definir_forma_ingresso/<int:pk>/', views.definir_forma_ingresso),
    path('inscricao_em_edital/<int:edital_id>/', views.inscricao_em_edital),
    path('inscricao_em_edital_xls/', views.inscricao_em_edital_xls),
    path('configuracaomigracaovaga/<int:pk>/', views.configuracaomigracaovaga),
    path('definir_precedencia_matricula/<int:pk>/', views.definir_precedencia_matricula),
    path('definir_precedencia/<int:pk>/', views.definir_precedencia),
    path('editar_precedencia/<int:pk>/<str:lista_origem>/', views.editar_precedencia),
    path('remover_precedencia/<int:pk>/<str:lista_origem>/', views.remover_precedencia),
    path('realizar_acao_lote/<int:pk>/', views.realizar_acao_lote),
    path('vincular_vaga/<int:pk>/', views.vincular_vaga),
    path('vincular_matricula/<int:pk>/', views.vincular_matricula),
    path('editar_oferta_vaga_curso/<int:pk>/', views.editar_oferta_vaga_curso),
    path('criar_vaga_remanescente/<int:pk>/', views.criar_vaga_remanescente),
]
