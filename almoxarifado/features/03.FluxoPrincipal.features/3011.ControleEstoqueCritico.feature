# -*- coding: utf-8 -*-
# language: pt

#Funcionalidade: Funcionalidades do menu Administração::Almoxarifado::Controle de Estoque Crítico
#    Essa funcionalidade é para testar o fluxo principal
#
#  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
#    Dado os usuarios do Almoxarifado
#    Quando acesso a página "/"
#    E realizo o login com o usuário "CoordDeAlmoxSiste" e senha "abcd"
#
##  Cenário falha com mensagem "Erro no sistem"
##
##  Cenario: Adicionar Material Controlado
##    Dado acesso a página "/"
##    Quando acesso a página "/almoxarifado/situacao_estoque"
##    E clico no botão "Adicionar Material Controlado"
##    E preencho o formulário com os dados
##        | Campo                  | Tipo         | Valor     |
##        | Tempo de Aquisição     | Texto        | 1         |
##        | Intervalo de Aquisição | Autocomplete | 1         |
##    E clico no botão "Enviar"
##    Então vejo a pagina "Situação do Estoque"
#
#  Cenário: Encerrando a feature
#    Dado acesso a página "/"
#    Quando acesso o menu "Sair"
