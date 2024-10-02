# -*- coding: utf-8 -*-
# language: pt

#Funcionalidade: Funcionalidades do menu Administração::Almoxarifado::Relatorios::Materiais Transferidos
#    Essa funcionalidade é para testar o fluxo principal
#
#  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
#    Dado os usuarios do Almoxarifado
#    Quando acesso a página "/"
#    E realizo o login com o usuário "CoordDeAlmoxSiste" e senha "abcd"
#
#  @do_document
#  Cenario: Visualizar Relatório de Materiais Transferidos
#    Dado acesso a página "/"
#    Quando acesso a página "/almoxarifado/materiais_transferidos/"
#    E preencho o formulário com os dados
#        | Campo                | Tipo         | Valor             |
#        | Solicitante          | Autocomplete | CoordDeAlmoxSiste |
#        | Data inicial         | Data         | 13/05/2019        |
#        | Data final           | Data         | 13/05/2019        |
#    E clico no botão "Enviar"
#    Então vejo a página "Materiais Transferidos"
#
#  Cenário: Encerrando a feature
#    Dado acesso a página "/"
#    Quando acesso o menu "Sair"
