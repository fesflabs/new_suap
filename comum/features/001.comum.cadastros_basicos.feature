# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastros Básicos
  Cadastro de Pessoa Jurídica, Prestadores de Servico e de Ocupação dos prestadores de serviço

  Contexto: Acessa a index da aplicação
    Dado acesso a página "/"

  Cenário: Efetuar login no sistema
    Quando realizo o login com o usuário "admin" e senha "abc"


  @do_document
  Cenário: Cadastrar Pessoa Jurídica
    Quando acesso o menu "Administração::Cadastros::Pessoas Jurídicas"
    Então vejo o botão "Adicionar Pessoa Jurídica"
    Quando clico no botão "Adicionar Pessoa Jurídica"
    Então vejo a página "Adicionar Pessoa Jurídica"
    Quando preencho o formulário com os dados
      | Campo        | Tipo  | Valor              |
      | Razão Social | Texto | Empresa X          |
      | CNPJ         | Texto | 50.834.073/0001-57 |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Cadastrar Prestadores de Serviço Brasileiro
    Quando acesso o menu "Administração::Cadastros::Prestadores de Serviço"
    Então vejo o botão "Adicionar Prestador de serviço"
    Quando clico no botão "Adicionar Prestador de serviço"
    Então vejo a página "Adicionar Prestador de serviço"
    Quando preencho o formulário com os dados
      | Campo            | Tipo   | Valor                |
      | Nome de Registro | Texto  | Prestador de Serviço |
      | CPF              | Texto  | 914.459.310-44       |
      | Nacionalidade    | Lista  | Brasileiro Nato      |
      | Sexo             | Lista  | Masculino            |
      | Setor            | Arvore | A1                   |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Cadastrar uma ocupação para o Prestador de Serviço
    Quando acesso o menu "Administração::Cadastros::Prestadores de Serviço"
    Quando olho para a listagem
    E olho a linha "Prestador de Serviço"
    E clico no ícone de exibição
    Então vejo a página "Prestador de Serviço (91445931044)"
    Então vejo o botão "Vincular Ocupação"
    Quando clico no botão "Vincular Ocupação"
    E olho para o popup
    Então vejo a página "Vincular Ocupação do Prestador Prestador de Serviço (91445931044)"
    Quando preencho o formulário com os dados
      | Campo          | Tipo         | Valor          |
      | Ocupacao       | Autocomplete | Teste Ocupação |
      | Pessoa Jurídica| Autocomplete | Empresa X      |
      | Data de início | Data         | 01/01/2020     |
      | Data fim       | Data         | 31/01/2020     |
      | Setor suap     | Autocomplete | A1             |
    E clico no botão "Salvar"

  @do_document
  Cenário: Cadastrar Prestadores de Serviço Estrangeiro
    Quando acesso o menu "Administração::Cadastros::Prestadores de Serviço"
    Então vejo o botão "Adicionar Prestador de serviço"
    Quando clico no botão "Adicionar Prestador de serviço"
    Então vejo a página "Adicionar Prestador de serviço"
    Quando preencho o formulário com os dados
      | Campo            | Tipo   | Valor                |
      | Nome de Registro | Texto  | Prestador de Serviço |
      | Nacionalidade    | Lista  | Estrangeiro          |
      | Nº do Passaporte | Texto  | 12314540152215       |
      | Sexo             | Lista  | Masculino            |
      | Setor            | Arvore | A1                   |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

