# -*- coding: utf-8 -*

from django.urls import path

from professor_titular import views

urlpatterns = [
    path('criar_processo_titular/', views.criar_processo_titular),
    path('abrir_processo_titular/<int:processo_id>/', views.abrir_processo_titular),
    path('salvar_processo_titular/<int:processo_id>/', views.salvar_processo_titular),
    path('enviar_processo_titular/<int:processo_id>/', views.enviar_processo_titular),
    path('professor_titular_upload/', views.professor_titular_upload, name='professor_titular_upload'),
    path('professor_titular_upload_documentos_exigidos/', views.professor_titular_upload_documentos_exigidos, name='professor_titular_upload_documentos_exigidos'),
    path('visualizar_arquivo_pdf/<str:arquivo_id>/', views.visualizar_arquivo_pdf),
    path('visualizar_arquivo_exigido_pdf/<str:arquivo_id>/', views.visualizar_arquivo_exigido_pdf),
    path('excluir_arquivo_pdf/<str:arquivo_id>/', views.excluir_arquivo_pdf),
    path('excluir_arquivo_exigido_pdf/<str:arquivo_id>/', views.excluir_arquivo_exigido_pdf),
    path('imprimir_processo/<int:processo_id>/', views.imprimir_processo),
    path('processo_capa/<int:processo_id>/', views.processo_capa),
    path('requerimento_pdf/<int:processo_id>/', views.requerimento_pdf),
    path('formulario_pontuacao_pdf/<int:processo_id>/', views.formulario_pontuacao_pdf),
    path('relatorio_descritivo_pdf/<int:processo_id>/', views.relatorio_descritivo_pdf),
    path('relatorio_descritivo/<int:processo_id>/', views.relatorio_descritivo),
    path('quadro_resumo_pontuacao_requerida/<int:processo_id>/', views.quadro_resumo_pontuacao_requerida),
    path('documentos_anexados_pdf/<int:processo_id>/', views.documentos_anexados_pdf),
    path('excluir_processo_titular/<int:processo_id>/', views.excluir_processo_titular),
    path('validar_processo_titular/<int:processo_id>/', views.validar_processo_titular),
    path('selecionar_avaliadores/<int:processo_id>/', views.selecionar_avaliadores),
    path('clonar_processo_titular/<int:processo_id>/', views.clonar_processo_titular),
    path('acompanhar_avaliacao/<int:processo_id>/', views.acompanhar_avaliacao),
    path('documentos_preliminares/<int:processo_id>/', views.documentos_preliminares),
    path('processo_avaliacao/', views.processo_avaliacao),
    path('imprimir_documentos_pdf/<int:processo_id>/', views.imprimir_documentos_pdf),
    path('encaminhamento_banca_pdf/<int:processo_id>/', views.encaminhamento_banca_pdf),
    path('recusar_avaliacao/<int:processo_avaliacao_id>/', views.recusar_avaliacao),
    path('ciencia_resultado/<int:processo_id>/', views.ciencia_resultado),
    path('termo_aceite/<int:processo_avaliacao_id>/', views.termo_aceite),
    path('aceitar_rejeitar_processo/<int:processo_id>/', views.aceitar_rejeitar_processo),
    path('avaliar_processo/<int:processo_id>/<int:avaliador_id>/', views.avaliar_processo),
    path('rejeitar_processo_cppd/<int:processo_id>/', views.rejeitar_processo_cppd),
    path('avaliar_item/<int:avaliacao_item_id>/', views.avaliar_item),
    path('salvar_avaliacao/<int:avaliacao_item_id>/', views.salvar_avaliacao),
    path('salvar_avancar_proximo/<int:avaliacao_item_id>/', views.salvar_avancar_proximo),
    path('pular_item/<int:avaliacao_item_id>/', views.pular_item),
    path('quadro_resumo_avaliacao/<int:avaliacao_id>/', views.quadro_resumo_avaliacao),
    path('finalizar_avaliacao/<int:avaliacao_id>/', views.finalizar_avaliacao),
    path('finalizar_avaliacao_titular/<int:avaliacao_id>/', views.finalizar_avaliacao_titular),
    path('desistir_avaliacao/<int:avaliacao_id>/', views.desistir_avaliacao),
    path('finalizar_processo/<int:processo_id>/', views.finalizar_processo),
    path('download_arquivos/<int:processo_id>/', views.download_arquivos),
    path('gerar_processo_completo/<int:processo_id>/', views.gerar_processo_completo),
    path('processos_pagamento_avaliador_interno/', views.processos_pagamento_avaliador_interno),
    path('processos_pagamento_avaliador_externo/', views.processos_pagamento_avaliador_externo),
    path('popup_avaliacao_pagamento_avaliador/<int:avaliador_id>/', views.popup_avaliacao_pagamento_avaliador),
    path('relatorio_pagamento/', views.relatorio_pagamento),
    path('relatorio_pagamento_pdf/', views.relatorio_pagamento_pdf),
    path('recalcular_pontuacao/<int:processo_id>/', views.recalcular_pontuacao, name='recalcular_pontuacao'),
]
