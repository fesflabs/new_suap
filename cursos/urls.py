# -*- coding: utf-8 -*

from django.urls import path
from cursos import views

urlpatterns = [
    path('curso/<int:id>/', views.curso),
    path('adicionar_horas/<int:id>/', views.adicionar_horas),
    path('horas_trabalhadas/<int:matricula_servidor>/', views.horas_trabalhadas),
    path('horas_trabalhadas/', views.horas_trabalhadas),
    path('curso/<int:id>/remover/', views.curso_remover),
    path('curso/<int:id>/iniciar/', views.curso_iniciar),
    path('curso/<int:id>/finalizar/', views.curso_finalizar),
    path('curso/<int:id>/informar_cadastro_folha/', views.informar_cadastro_folha),
    path('add_participante/<int:curso_id>/', views.add_participante),
    path('remover_participante/<int:participante_id>/', views.remover_participante),
    path('editar_participante/<int:participante_id>/', views.editar_participante),
    path('deferir_participacao/<int:participante_id>/', views.deferir_participacao),
    path('indeferir_participacao/<int:participante_id>/', views.indeferir_participacao),
    path('cota_anual_servidor/', views.cota_anual_servidor),
    path('liberar_participantes/<int:curso_id>/', views.liberar_participantes),
    path('editar_mes_pagamento/<int:participante_id>/', views.editar_mes_pagamento),
    path('hora_prevista_to_hora_trabalhada/<int:curso_id>/', views.hora_prevista_to_hora_trabalhada),
    path('realizar_pagamento_participante_pendente/<int:curso_id>/<int:participante_id>/', views.realizar_pagamento_participante_pendente),
    path('participantes_pendentes_pagamento/', views.participantes_pendentes_pagamento),
    # relatórios
    path('imprimir_listagem/<int:curso_id>/', views.imprimir_listagem),
    path('relatorio_pagamento/', views.relatorio_pagamento),
    path('relatorio_pagamento_gecc_pdf/<int:mes>/<int:ano>/', views.relatorio_pagamento_gecc_pdf),
]
