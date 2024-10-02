# -*- coding: utf-8 -*
from django.urls import path

from gerenciador_projetos import views

urlpatterns = [
    path('projeto/<int:projeto_id>/', views.projeto, name='projeto'),
    path('projeto/<int:projeto_id>/dashboard/', views.dashboard, name='dashboard'),
    path('projeto/<int:projeto_id>/gantt/', views.gantt, name='gantt'),
    path('projeto/<int:projeto_id>/tarefa/adicionar/', views.gerenciar_tarefa, name='adicionar_tarefa'),
    path('projeto/<int:projeto_id>/tarefa/adicionar/api/', views.gerenciar_tarefa_api, name='adicionar_tarefa_api'),
    path('projeto/<int:projeto_id>/tarefa/<int:tarefa_id>/', views.gerenciar_tarefa, name='alterar_tarefa'),
    path('projeto/<int:projeto_id>/clonar/', views.clonar_projeto, name='clonar_projeto'),
    path('projeto/<int:projeto_id>/listaprojeto/', views.adicionar_ou_vincular_lista_projeto, name='adicionar_ou_vincular_lista_projeto'),
    path('adicionar_tag/<int:projeto_id>/', views.adicionar_tag, name='adicionar_tag'),
    path('editar_tag/<int:tag_id>/', views.editar_tag, name='editar_tag'),
    path('listaprojeto/<int:lista_projeto_id>/', views.atualizar_posicao_lista_projeto, name='atualizar_posicao_lista_projeto'),
    path('tarefa/<int:tarefa_id>/', views.tarefa, name='tarefa'),
    path('tarefa/<int:tarefa_id>/editar_tarefa/', views.editar_tarefa, name='editar_tarefa'),
    path('tarefa/<int:tarefa_id>/clonar/', views.clonar_tarefa, name='clonar_tarefa'),
    path('tarefa/<int:tarefa_id>/historicoevolucao/adicionar/', views.gerenciar_historicoevolucao, name='gerenciar_historicoevolucao'),
    path('tarefa/<int:tarefa_id>/mudarlista/<int:lista_id>/<int:posicao>/', views.mudarlista, name='mudarlista'),
    path('tarefa/<int:tarefa_id>/recorrencia/', views.recorrencia_tarefa, name='recorrencia_tarefa'),
    path('tarefa/<int:tarefa_id>/reabrir/', views.reabrir_tarefa, name='reabrir_tarefa'),
    path('atribuir_a_mim/<int:tarefa_id>/', views.atribuir_a_mim, name='atribuir_a_mim'),
    path('recorrenciatarefa/<int:recorrenciatarefa_id>/remover/', views.remover_recorrencia_tarefa, name='remover_recorrencia_tarefa'),
    path('minhastarefas/', views.minhas_tarefas, name='minhas_tarefas'),
    path('status_projeto/<int:projeto_id>/', views.status_projeto, name='status_projeto'),
    path('evolucao_tarefas_projeto/<int:projeto_id>/', views.evolucao_tarefas_projeto, name='evolucao_tarefas_projeto'),
]


"""
    modelo/add/             # Incluir
    modelo/{{id}}/          # Alterar
    modelo/{{id}}/delete/   # Excluir
    modelo/{{id}}/view/     # Visualizar
"""
