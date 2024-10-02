# -*- coding: utf-8 -*-
# language: pt

#Funcionalidade: Funcionalidades do menu Administração::Almoxarifado::Relatorios::Balancete::Elemento de Despesa Detalhado
#    Essa funcionalidade é para testar o fluxo principal
#
#  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
#    Dado os usuarios do Almoxarifado
#    Quando acesso a página "/"
#    E realizo o login com o usuário "CoordDeAlmoxSiste" e senha "abcd"
#
#  @do_document
#  Cenario: Visualizar Balancete de Material de Consumo
#    Dado acesso a página "/"
#    Quando acesso a página "/almoxarifado/balancete_ed_detalhado/"
#    E preencho o formulário com os dados
#        | Campo                | Tipo     | Valor                          |
#        | Elemento de despesa  | Lista    | Categoria Material Consumo     |
#        | Data inicial         | Data     | 07/05/2019                     |
#        | Data final           | Data     | 07/05/2019                     |
#    E clico no botão "Enviar"
#    Então vejo a página "Balancete Elemento de Despesa Detalhado"
#
#  Cenário: Encerrando a feature
#    Dado acesso a página "/"
#    Quando acesso o menu "Sair"
