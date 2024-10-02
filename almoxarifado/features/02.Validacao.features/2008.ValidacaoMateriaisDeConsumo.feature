## -*- coding: utf-8 -*-
## language: pt
#
#
#Funcionalidade: Testando autorização do menu Administração::Almoxarifado::Materiais de Consumo
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
#  # Elementos de Despesa de Mat. de Consumo
#
#  #Cenários falham pois usuário não consegue visualizar o botão
#
##  Cenário: Adicionar Elementos de Despesa de Mat. de Consumo
##    Dado acesso a página "/"
##    Quando acesso a página "/admin/almoxarifado/categoriamaterialconsumo/"
##    E clico no botão "Adicionar Elemento de Despesa de Mat. de Consumo"
##    Então vejo os seguintes campos no formulário
##      | Campo                           | Tipo                |
##      | Código                          | Texto               |
##      | Nome                            | Texto               |
##    Quando clico no botão "Salvar"
##    Então vejo mensagem de erro "Por favor, corrija os erros abaixo."
##    E vejo os seguintes erros no formulário
##      | Campo                           | Mensagem                  |
##      | Código                          | Este campo é obrigatório. |
##      | Nome                            | Este campo é obrigatório. |
#
##  Cenário: Adicionar Elementos de Despesa de Mat. de Consumo
##    Dado acesso a página "/"
##    Quando acesso a página "/admin/almoxarifado/categoriamaterialconsumo/"
##    E clico no botão "Adicionar Elemento de Despesa de Mat. de Consumo"
##    Quando preencho o formulário com os dados
##      | Campo                           | Tipo                | Valor         |
##      | Código                          | Texto               | 01            |
##      | Nome                            | Texto               | Teste         |
##    E clico no botão "Salvar"
##    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."
#
#  # Material de Consumo
#
#  Cenário: Adicionar Material de Consumo
#    Dado acesso a página "/"
#    Quando acesso a página "/admin/almoxarifado/materialconsumo/"
#    E clico no botão "Adicionar Material de Consumo"
#    Então vejo os seguintes campos no formulário
#      | Campo                          | Tipo               |
#      | Categoria                      | Autocomplete       |
#      | Nome                           | Textarea           |
#    Quando clico no botão "Salvar"
#    Então vejo mensagem de erro "Por favor, corrija os erros abaixo."
#    E vejo os seguintes erros no formulário
#      | Campo                           | Mensagem                  |
#      | Categoria                       | Este campo é obrigatório. |
#      | Nome                            | Este campo é obrigatório. |
#
#  Cenário: Adicionar Material de Consumo
#    Dado acesso a página "/"
#    Quando acesso a página "/admin/almoxarifado/materialconsumo/"
#		E clico no botão "Adicionar Material de Consumo"
#    Quando preencho o formulário com os dados
#      | Campo                          | Tipo               | Valor         |
#      | Categoria                      | Autocomplete       | 0             |
#      | Nome                           | Textarea           | Teste         |
#    Quando clico no botão "Salvar"
#    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."
#
#  # =============================================================================
#  # =========================== Modificar/Editar ================================
#  # =============================================================================
#  
#  # Elementos de Despesa de Mat. de Consumo  
#
#  #Cenários falham pois usuário não consegue visualizar o botão
#
##  Cenário: Editar Elementos de Despesa de Mat. de Consumo
##    Dado acesso a página "/"
##    Quando acesso a página "/admin/almoxarifado/categoriamaterialconsumo/"
##    E clico no ícone de edição
##    Então vejo os seguintes campos no formulário
##      | Campo                           | Tipo                |
##      | Código                          | Texto               |
##      | Nome                            | Texto               |
##    Quando clico no botão "Salvar"
##    Então vejo mensagem de sucesso "Atualização realizada com sucesso."
##
##  # Materiais de Consumo
##
##  Cenário: Editar Material de Consumo
##    Dado acesso a página "/"
##    Quando acesso a página "/admin/almoxarifado/materialconsumo"
##    E clico no ícone de edição
##    Então vejo os seguintes campos no formulário
##      | Campo                          | Tipo               |
##      | Categoria                      | Autocomplete       |
##      | Nome                           | Textarea           |
##    Quando clico no botão "Salvar"
##    Então vejo mensagem de sucesso "Atualização realizada com sucesso."
#
#  # =============================================================================
#  # ================================= Apagar ====================================
#  # =============================================================================
