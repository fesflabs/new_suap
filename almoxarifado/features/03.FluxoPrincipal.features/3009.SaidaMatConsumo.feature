# -*- coding: utf-8 -*-
# language: pt

#Funcionalidade: Funcionalidades do menu Administração::Almoxarifado::Requisições::Requisição de Saída de Material para Consumo
#    Essa funcionalidade é para testar o fluxo principal
#
#  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
#    Dado os usuarios do Almoxarifado
#    Quando acesso a página "/"
#    E realizo o login com o usuário "CoordDeAlmoxSiste" e senha "abcd"
#
##  Cenário falha pois campo "Material" (autocomplete) não funciona
##
##  Cenario: Visualizar Requisição de Saída de Material para Consumo
##    Dado acesso a página "/"
##    Quando acesso a página "/almoxarifado/form_requisicao_usuario_pedido"
##    E preencho o formulário com os dados
##        | Campo                | Tipo              | Valor             |
##        | Material             | Autocomplete      | Material          |
##        | Quantidade           | Autocomplete      | 1                 |
##    E clico no botão "Efetuar"
##    Então vejo a página "Requisição de Saída de Material para Consumo"
#
#  Cenário: Encerrando a feature
#    Dado acesso a página "/"
#    Quando acesso o menu "Sair"
