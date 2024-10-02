# -*- coding: utf-8 -*-
# language: pt

#Funcionalidade: Funcionalidades do menu Administração::Almoxarifado::Requisições::Transferência de Material Intercampi
#    Essa funcionalidade é para testar o fluxo principal
#
#  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
#    Dado os usuarios do Almoxarifado
#    Quando acesso a página "/"
#    E realizo o login com o usuário "CoordDeAlmoxSiste" e senha "abcd"
#
##  Cenário falha pois campo "Material" (autocomplete) não funciona
##
##  Cenario: Visualizar Requisição de Transferência de Material de Consumo Intercampi
##    Dado acesso a página "/"
##    Quando acesso a página "/almoxarifado/form_requisicao_uo_pedido"
##    E preencho o formulário com os dados
##        | Campo                | Tipo              | Valor             |
##        | Material             | Autocomplete      | Material          |
##        | Quantidade           | Autocomplete      | 1                 |
##    E clico no botão "Efetuar"
##    Então vejo a página "Requisição de Transferência de Material de Consumo Intercampi"
#
#
#  Cenário: Encerrando a feature
#    Dado acesso a página "/"
#    Quando acesso o menu "Sair"
