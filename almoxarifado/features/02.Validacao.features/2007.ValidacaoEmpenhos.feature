## -*- coding: utf-8 -*-
## language: pt
#
#
#Funcionalidade: Testando autorização do menu Administração::Almoxarifado::Empenhos
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
#  Cenário: Adicionar Empenhos
#    Dado acesso a página "/"
#    Quando acesso a página "/almoxarifado/empenhos/"
#    E clico no botão "Adicionar Empenho"
#    Então vejo os seguintes campos no formulário
#      | Campo                          | Tipo               |
#      | Número de empenho              | Texto              |
#      | Processo                       | Autocomplete       |
#      | Tipo de Material               | Autocomplete       |
#      | Tipo de Fornecedor             | Checkbox Multiplo  |
#    Quando clico no botão "Salvar"
#    Então vejo mensagem de erro "Por favor, corrija os erros abaixo."
#    E vejo os seguintes erros no formulário
#      | Campo                          | Mensagem                  |
#      | Número de empenho              | Este campo é obrigatório. |
#      | Processo                       | Este campo é obrigatório. |
#      | Tipo de Material               | Este campo é obrigatório. |
#      | Tipo de Fornecedor             | Este campo é obrigatório. |
#
#      # 
#      #   O indicador de campo obrigatório e a mensagem de erro (quando verificado no teste) estão
#      #   para o campo "Tipo de Fornecedor" enquanto a mensagem do erro (para o usuário) está no campo
#      #   "Pessoa Física" 
#      # 
#
##  Cenário: Adicionar Empenhos
##    Dado acesso a página "/"
##    Quando acesso a página "/almoxarifado/empenhos/"
##    E clico no botão "Adicionar Empenho"
##    Quando preencho o formulário com os dados
##      | Campo                          | Tipo               | Valor                 |
##      | Número de empenho              | Texto              | 9999NE123456          |
##      | Processo                       | Autocomplete       | 23002.000001.2019-58  |
##      | Tipo de Material               | Autocomplete       | Consumo               |
##      | Tipo de Fornecedor             | Checkbox Multiplo  | Pessoa Física         |
##    Quando clico no botão "Salvar"
##    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."
#
#    # Mensagem de campo obrigatório está aparecendo no campo de Pessoa Física
#
#    # Erros:
#    # NÃO FOI POSSÍVEL CADASTRAR UM NOVO PROCESSO PARA REALIZAR ESSE TESTE