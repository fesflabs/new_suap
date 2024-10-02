## -*- coding: utf-8 -*-
## language: pt
#
#
#Funcionalidade: Testando autorização do menu Administração::Almoxarifado::Plano de Contas
#  Essa funcionalidade é para testar se de acordo com as autorizações o usuário pode acessar apenas os itens permitidos
#
#  Cenário: Adiciona os usuários necessários para esse teste
#    Dado os usuarios do Almoxarifado
#    Quando acesso a página "/"
#    E realizo o login com o usuário "ContadorAdministra" e senha "abcd"
#
#  # =============================================================================
#  # ============================== Adicionar ====================================
#  # =============================================================================
#
#  Cenário: Adicionar Plano de Contas
#    Dado acesso a página "/"
#    Quando acesso a página "/admin/almoxarifado/planocontasalmox/"
#    E clico no botão "Adicionar Plano de Contas"
#    Então vejo os seguintes campos no formulário
#        | Campo                           | Tipo                |
#        | Código                          | Texto               |
#        | Descrição                       | Texto               |
#    Quando clico no botão "Salvar"
#    Então vejo mensagem de erro "Por favor, corrija os erros abaixo." 
#    E vejo os seguintes erros no formulário
#        | Campo                          | Mensagem                  |
#        | Código                         | Este campo é obrigatório  |
#        | Descrição                      | Este campo é obrigatório  |
#    
#  Cenário: Adicionar Plano de Contas
#    Dado acesso a página "/"
#    Quando acesso a página "/admin/almoxarifado/planocontasalmox/"
#    E clico no botão "Adicionar Plano de Contas"
#    Quando preencho o formulário com os dados
#      | Campo                           | Tipo                | Valor         |
#      | Código                          | Texto               | 01            |
#      | Descrição                       | Texto               | Teste         |
#    E clico no botão "Salvar"
#    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."
#
#  # =============================================================================
#  # =========================== Modificar/Editar ================================
#  # =============================================================================
#
#  Cenário: Editar Plano de Contas
#		Dado acesso a página "/"
#		Quando acesso a página "/admin/almoxarifado/planocontasalmox/"
#		E clico no ícone de edição
#		Então vejo os seguintes campos no formulário
#      | Campo                           | Tipo                |
# 	    | Código                          | Texto               |
#			| Descrição                       | Texto               |
#		Quando clico no botão "Salvar"
#    Então vejo mensagem de sucesso "Atualização realizada com sucesso."
# 
#  # =============================================================================
#  # ================================= Apagar ====================================
#	# =============================================================================
#	
#  Cenário: Editar Plano de Contas
#		Dado acesso a página "/"
#		Quando acesso a página "/admin/almoxarifado/planocontasalmox/"
#		E clico no ícone de edição	
#		E clico no link "Apagar"
#		Quando preencho o formulário com os dados
#			| Campo | Tipo 	| Valor |
#			| Senha	| Texto	|	abcd	|
#		E clico no botão "Sim, tenho certeza"
#    Então vejo mensagem de sucesso "excluído com sucesso."
#
