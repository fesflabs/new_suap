# -*- coding: utf-8 -*-
# language: pt

#Funcionalidade: Funcionalidades do menu Administração::Almoxarifado::Relatorios::Saída por Setor
#    Essa funcionalidade é para testar o fluxo principal
#
#  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
#    Dado os usuarios do Almoxarifado
#    Quando acesso a página "/"
#    E realizo o login com o usuário "CoordDeAlmoxSiste" e senha "abcd"
#
##  Cenário falha porque o campo do tipo "árvore" não é reconhecido
##
##  Cenario: Visualizar Relatório de Saída por Setor
##    Dado acesso a página "/"
##    Quando acesso a página "/almoxarifado/relatorio/consumo_setor/"
##    E preencho o formulário com os dados
##        | Campo                | Tipo              | Valor             |
##        | Setor                | Arvore            | RE                |
##        | Data inicial         | Data              | 13/05/2019        |
##        | Data final           | Data              | 13/05/2019        |
##        | Opcao exibir         | Checkbox multiplo | Todas as Saídas   |
##    E clico no botão "Enviar"
##    Então vejo a página "Saída por Setor"
#
#  Cenário: Encerrando a feature
#    Dado acesso a página "/"
#    Quando acesso o menu "Sair"
