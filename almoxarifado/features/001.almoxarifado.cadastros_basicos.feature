# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastros Básicos
    Cadastro de Unidades de Medida, Material de Consumo, Plano de Contas e Elementos de Despesa de Mat. de Consumo.

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do Almoxarifado
    Quando acesso a página "/"
    E realizo o login com o usuário "admin" e senha "abc"

  @do_document
  Cenario: Cadastrar Unidades de Medida
    Dado acesso a página "/"
    Quando acesso a página "/admin/almoxarifado/unidademedida/"
    E clico no botão "Adicionar Unidade de Medida"
    Quando preencho o formulário com os dados
        | Campo    | Tipo         | Valor                    |
        | Nome     | Texto        | Teste Unidade de Medida  |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso"

  Cenario: Visualizar Unidade de Medida
    Dado acesso a página "/"
    E acesso a página "/admin/almoxarifado/unidademedida/"
    Então vejo mais de 0 resultados na tabela

  Cenario: Editar Unidade de Medida
    Dado acesso a página "/"
    E acesso a página "/admin/almoxarifado/unidademedida/"
    Quando clico no link "Teste Unidade de Medida"
    E preencho o formulário com os dados
        | Campo       | Tipo         | Valor                    |
        | Nome        | Texto        | Nova Unidade de Medida   |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso"

  Cenario: Apagar Unidade de Medida
    Dado acesso a página "/"
    Quando acesso a página "/admin/almoxarifado/unidademedida/"
    E clico no link "Nova Unidade de Medida"
    E clico no link "Apagar"
    Quando preencho o formulário com os dados
        | Campo             | Tipo         | Valor       |
        | Senha             | senha        | abc         |
    E clico no botão "Sim, remova"
    Então vejo mensagem de sucesso "excluído com sucesso"
    Quando acesso o menu "Sair"



  @do_document
  Cenario: Cadastrar Material de Consumo
    Dado acesso a página "/"
    Quando realizo o login com o usuário "CoordDeAlmoxSiste" e senha "abcd"
    E acesso a página "/admin/almoxarifado/materialconsumo/"
    E clico no botão "Adicionar Material de Consumo"
    E preencho o formulário com os dados
        | Campo          | Tipo          | Valor                       |
        | Categoria      | Autocomplete  | Categoria Material Consumo  |
        | Nome           | Textarea      | Material Teste              |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso"
    E vejo mais de 0 resultados na tabela

  Cenario: Editar Material de Consumo
    Dado acesso a página "/"
    E acesso a página "/admin/almoxarifado/materialconsumo/"
    Quando clico no ícone de edição
    E preencho o formulário com os dados
        | Campo          | Tipo          | Valor                |
        | Nome           | Textarea      | Novo Material Teste  |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso"
    Quando acesso o menu "Sair"


  @do_document
  Cenario: Cadastrar Plano de Contas
    Dado acesso a página "/"
    Quando realizo o login com o usuário "ContadorAdministra" e senha "abcd"
    Quando acesso a página "/admin/almoxarifado/planocontasalmox/"
    E clico no botão "Adicionar Plano de Contas"
    E preencho o formulário com os dados
        | Campo          | Tipo     | Valor           |
        | Código         | Texto    | 3014            |
        | Descrição      | Texto    | Plano de Contas |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso"

  Cenario: Visualizar Plano de Contas
    Dado acesso a página "/"
    E acesso a página "/admin/almoxarifado/planocontasalmox/"
    Então vejo mais de 0 resultados na tabela

  Cenario: Editar Plano de Contas
    Dado acesso a página "/"
    E acesso a página "/admin/almoxarifado/planocontasalmox/"
    Quando clico no ícone de edição
    E preencho o formulário com os dados
        | Campo          | Tipo     | Valor                |
        | Código         | Texto    | Novo3014             |
        | Descrição      | Texto    | Novo Plano de Contas |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso"

  Cenario: Apagar Plano de Contas
    Dado acesso a página "/"
    Quando acesso a página "/admin/almoxarifado/planocontasalmox/"
    E olho a linha "Novo Plano de Contas"
    E clico no ícone de edição
    E clico no link "Apagar"
    Quando preencho o formulário com os dados
        | Campo             | Tipo         | Valor       |
        | Senha             | senha        | abcd        |
    E clico no botão "Sim, remova"
    Então vejo mensagem de sucesso "excluído com sucesso"
    Quando acesso o menu "Sair"


  @do_document
  Cenario: Cadastrar Elemento de Despesa de Mat. de Consumo
    Dado acesso a página "/"
    Quando realizo o login com o usuário "admin" e senha "abc"
    Quando acesso a página "/admin/almoxarifado/categoriamaterialconsumo/"
    E clico no botão "Adicionar Elemento de Despesa de Mat. de Consumo"
    Quando preencho o formulário com os dados
        | Campo         | Tipo         | Valor                      |
        | Código        | Texto        | 3002                       |
        | Nome          | Texto        | Teste Elemento             |
        | Plano contas  | Autocomplete | ALMOXARIFADO               |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso"

  Cenario: Visualizar Elemento de Despesa de Mat. de Consumo
    Dado acesso a página "/"
    E acesso a página "/admin/almoxarifado/categoriamaterialconsumo/"
    Então vejo mais de 0 resultados na tabela

  Cenario: Editar Elemento de Despesa de Mat. de Consumo
    Dado acesso a página "/"
    E acesso a página "/admin/almoxarifado/categoriamaterialconsumo/"
    Quando clico no ícone de edição
    E preencho o formulário com os dados
        | Campo         | Tipo         | Valor                              |
        | Código        | Texto        | 30021                              |
        | Nome          | Texto        | Novo Teste Elemento                |
        | Plano contas  | Autocomplete | MATERIAIS DE CONSUMO               |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso"

  Cenario: Apagar Elemento de Despesa de Mat. de Consumo
    Dado acesso a página "/"
    Quando acesso a página "/admin/almoxarifado/categoriamaterialconsumo/"
    Quando clico no ícone de edição
    E clico no link "Apagar"
    Quando preencho o formulário com os dados
        | Campo             | Tipo         | Valor       |
        | Senha             | senha        | abc         |
    E clico no botão "Sim, remova"
    Então vejo mensagem de sucesso "excluído com sucesso"


