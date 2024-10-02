# -*- coding: utf-8 -*-
# language: pt

#Funcionalidade: Funcionalidades do menu Administração::Almoxarifado::Empenhos
#    Essa funcionalidade é para testar o fluxo principal
#
#  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
#    Dado os usuarios do Almoxarifado
#    Quando acesso a página "/"
#    E realizo o login com o usuário "CoordDeAlmoxSiste" e senha "abcd"
#
## Cenario falha pois objeto "Processo" não consegue ser adicionado aos dados iniciais
##  Cenario: Adicionar Empenho
##    Dado acesso a página "/"
##    Quando acesso a página "/almoxarifado/empenhos"
##    E clico no botão "Adicionar Empenho"
##    E preencho o formulário com os dados
##        | Campo                  | Tipo         | Valor      |
##        | Número de empenho      | Texto        | 20193012RE |
##        | Processo               | Autocomplete | 000001     |
##        | Tipo de Material       | Autocomplete | Consumo    |
##    E clico no botão "Salvar"
##    Então vejo a pagina ""
#
#  Cenário: Encerrando a feature
#    Dado acesso a página "/"
#    Quando acesso o menu "Sair"
