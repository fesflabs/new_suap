## -*- coding: utf-8 -*-
## language: pt
#
#
#Funcionalidade: Testando autorização do menu Administração::Almoxarifado::Entradas
#  Essa funcionalidade é para testar se de acordo com as autorizações o usuário pode acessar apenas os itens permitidos
#
#  Cenário: Adiciona os usuários necessários para esse teste
#    Dado os usuarios do Almoxarifado
#    Quando acesso a página "/"
#    E realizo o login com o usuário "CoordDeAlmoxSiste" e senha "abcd"
#	# =============================================================================
#	# ===============================  Busca  =====================================
#  # =============================================================================
#	
#	# Teste impossibilitado por falta de label no input	
#	
#  # =============================================================================
#  # ============================== Adicionar ====================================
#  # =============================================================================
#
#  Cenário: Adicionar Entradas de Compra
#    Dado acesso a página "/"
#    Quando acesso a página "/almoxarifado/entrada_busca/"
#    E clico no botão "Adicionar Compra"
#    Então vejo os seguintes campos no formulário
#      | Campo                           | Tipo                |
#      | Campus                          | Texto               |
#      | Data Entrada                    | Data                |
#      | Empenho                         | Texto               |
#      | Campus                          | Texto               |
#      | Tipo Entrada                    | Texto               |
#      | Fornecedor                      | Texto               |
#      | Nº Nota Fiscal                  | Texto               |
#      | Data Nota Fiscal                | Data                |
#    Quando clico no botão "Efetuar"
#    Então vejo mensagem de erro "O campo EMPENHO está inválido" 
#
#
#  # 
#  # Essa página está com os componentes fora do padrão, logo as declarações
#  # "clico no botão" e "vejo os seguintes erros no formulário" não funcionam
#  #
#  
#  # =============================================================================
#  # =========================== Modificar/Editar ================================
#  # =============================================================================
#  
#  
#  # =============================================================================
#  # ================================= Apagar ====================================
#  # =============================================================================
