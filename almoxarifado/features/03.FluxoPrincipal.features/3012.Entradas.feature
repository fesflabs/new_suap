# -*- coding: utf-8 -*-
# language: pt

#Funcionalidade: Funcionalidades do menu Administração::Almoxarifado::Entradas
#    Essa funcionalidade é para testar o fluxo principal
#
#  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
#    Dado os usuarios do Almoxarifado
#    Quando acesso a página "/"
#    E realizo o login com o usuário "CoordDeAlmoxSiste" e senha "abcd"
#
## Cenário falha pois campo "Empenho" (autocomplete) não funciona
##
##  Cenario: Efetuar Entrada de Compra
##    Dado acesso a página "/"
##    Quando acesso a página "/almoxarifado/entrada_compra"
##    E clico no botão "Efetuar Entrada de Compra"
##    E preencho o formulário com os dados
##        | Campo                  | Tipo         | Valor      |
##        | Empenho                | Autocomplete | 20193012RE |
##        | Fornecedor             | Texto        | Fornecedor |
##        | Nº Nota Fiscal         | Texto        | 0000000000 |
##        | Data Nota Fiscal       | Data         | 21/05/2019 |
##    E clico no botão "Efetuar"
##    Então vejo a pagina ""
#
#  Cenário: Encerrando a feature
#    Dado acesso a página "/"
#    Quando acesso o menu "Sair"
