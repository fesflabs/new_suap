## -*- coding: utf-8 -*-
## language: pt
#
#
#Funcionalidade: Testando autorização do menu Administração::Almoxarifado::Controle de Estoque Crítico
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
#  Cenário: Adicionar Material Controlado
#    Dado acesso a página "/"
#    Quando acesso a página "/almoxarifado/situacao_estoque/"
#		E clico no botão "Adicionar Material Controlado"
#    Então vejo os seguintes campos no formulário
#      | Campo                           | Tipo                |
#      | Tempo de Aquisição              | Numero			        |
#      | Intervalo de Aquisição          | Numero			        |
#    Quando clico no botão "Enviar"
#    Então vejo mensagem de erro "Por favor, corrija os erros abaixo."
#    E vejo os seguintes erros no formulário
#      | Campo                           | Mensagem                  |
#      | Tempo de Aquisição              | Este campo é obrigatório. |
#      | Intervalo de Aquisição          | Este campo é obrigatório. |
#	
#	Cenário: Adicionar Material Controlado
#    Dado acesso a página "/"
#    Quando acesso a página "/almoxarifado/situacao_estoque/"
#		E clico no botão "Adicionar Material Controlado"
#   	Quando preencho o formulário com os dados
#      | Campo                           | Tipo                | Valor |
#      | Tempo de Aquisição              | Texto				        | 1			|
#			| Intervalo de Aquisição          | Texto				        | 1			|
#		Quando clico no botão "Enviar"
#		Então nao vejo mensagem de erro "Por favor, corrija os erros abaixo"
#
#		# aparece mensagem de erro do sistema falando que vai mandar um email
#
#	# =============================================================================
#  # =========================== Modificar/Editar ================================
#  # =============================================================================
#  
#  # =============================================================================
#  # ================================= Apagar ====================================
#	# =============================================================================
#	
#
