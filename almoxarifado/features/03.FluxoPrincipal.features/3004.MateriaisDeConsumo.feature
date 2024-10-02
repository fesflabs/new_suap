# -*- coding: utf-8 -*-
# language: pt
#
#Funcionalidade: Funcionalidades do menu Administração::Almoxarifado::Materiais de Consumo
#    Essa funcionalidade é para testar o fluxo principal
#
#  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
#    Dado os usuarios do Almoxarifado
#    Quando acesso a página "/"
#    E realizo o login com o usuário "CoordDeAlmoxSiste" e senha "abcd"
#
#  @do_document
#  Cenario: Adicionar e Visualizar o Material de Consumo adicionado
#    Dado acesso a página "/"
#    Quando acesso a página "/admin/almoxarifado/materialconsumo/"
#    E clico no botão "Adicionar Material de Consumo"
#    E preencho o formulário com os dados
#        | Campo          | Tipo          | Valor                       |
#        | Categoria      | Autocomplete  | Categoria Material Consumo  |
#        | Nome           | Textarea      | Material Teste              |
#    E clico no botão "Salvar"
#    Então vejo mensagem de sucesso "Cadastro realizado com sucesso"
#    E vejo mais de 0 resultados na tabela
#
#  @do_document
#  Cenario: Editar Material de Consumo
#    Dado acesso a página "/"
#    E acesso a página "/admin/almoxarifado/materialconsumo/"
#    Quando clico no ícone de edição
#    E preencho o formulário com os dados
#        | Campo          | Tipo          | Valor                |
#        | Nome           | Textarea      | Novo Material Teste  |
#    E clico no botão "Salvar"
#    Então vejo mensagem de sucesso "Atualização realizada com sucesso"
#
#  Cenário: Encerrando a feature
#    Dado acesso a página "/"
#    Quando acesso o menu "Sair"