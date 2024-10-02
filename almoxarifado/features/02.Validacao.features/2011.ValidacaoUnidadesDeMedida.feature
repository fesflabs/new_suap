## -*- coding: utf-8 -*-
## language: pt
#
#
#Funcionalidade: Testando autorização do menu Administração::Almoxarifado::Unidades de Medida
#  Essa funcionalidade é para testar se de acordo com as autorizações o usuário pode acessar apenas os itens permitidos
#
#  Cenário: Adiciona os usuários necessários para esse teste
#    Dado os usuarios do Almoxarifado
#    Quando acesso a página "/"
#    E realizo o login com o usuário "CoordDeAlmoxSiste" e senha "abcd"
#
#  # =============================================================================
#  # ============================== Adicionar ====================================
#  # =============================================================================
#
#  Cenário: Adicionar Unidades de Medida
#    Dado acesso a página "/"
#    Quando acesso a página "/admin/almoxarifado/unidademedida/"
#    E clico no botão "Adicionar Unidade de Medida"
#    Então vejo os seguintes campos no formulário
#      | Campo                           | Tipo                |
#      | Nome                            | Texto               |
#    Quando clico no botão "Salvar"
#    Então vejo mensagem de erro "Por favor, corrija o erro abaixo."
#    E vejo os seguintes erros no formulário
#      | Campo                           | Mensagem                  |
#      | Nome                            | Este campo é obrigatório. |
#	
#	Cenário: Adicionar Unidades de Medida
#    Dado acesso a página "/"
#    Quando acesso a página "/admin/almoxarifado/unidademedida/"
#    E clico no botão "Adicionar Unidade de Medida"
#    Quando preencho o formulário com os dados
#      | Campo		| Tipo    | Valor 	|
#      | Nome    | Texto		| Teste		|
#		Quando clico no botão "Salvar"
#		Então vejo mensagem de sucesso "Cadastro realizado com sucesso."
#
#	# =============================================================================
#  # =========================== Modificar/Editar ================================
#  # =============================================================================
#  
# 	Cenário: Editar Unidades de Medida
#		Dado acesso a página "/"
#		Quando acesso a página "/admin/almoxarifado/unidademedida/"
#		E clico no link "Teste"
#    Então vejo os seguintes campos no formulário
#      | Campo                           | Tipo                |
#			| Nome                            | Texto               |
#		Quando clico no botão "Salvar"
#    Então vejo mensagem de sucesso "Atualização realizada com sucesso." 
#
#
#  # =============================================================================
#  # ================================= Apagar ====================================
#	# =============================================================================
#	
#
