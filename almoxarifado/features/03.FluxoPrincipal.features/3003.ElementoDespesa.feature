# -*- coding: utf-8 -*-
# language: pt

#Funcionalidade: Funcionalidades do menu Administração::Almoxarifado::Relatorios::Balancete::Elemento de Despesa
#    Essa funcionalidade é para testar o fluxo principal
#
#  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
#    Dado os usuarios do Almoxarifado
#    Quando acesso a página "/"
#    E realizo o login com o usuário "CoordDeAlmoxSiste" e senha "abcd"

# Cenário falha pois existem 2 inputs de datas porém só o primeiro é capturado pelo teste
#
#  Cenario: Visualizar Balancete de Elemento de Despesa
#    Dado acesso a página "/"
#    Quando acesso a página "/almoxarifado/balancete_ed/"
#    E preencho o formulário com os dados
#        | Campo         | Tipo         | Valor      |
#        | Faixa         | Data         | 06/05/2019 |
#    E clico no botão "Enviar"
#    Então vejo a página "Balancete Elemento de Despesa de Material de Consumo"

#  Cenário: Encerrando a feature
#    Dado acesso a página "/"
#    Quando acesso o menu "Sair"
