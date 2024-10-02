# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Cadastrar Questionário

  @do_document
  Cenário: Cadastrar Questionário CPA
    Ação executada pelo membro do grupo cpa_gerente.

    Dado acesso a página "/"
    Quando realizo o login com o usuário "802021" e senha "abcd"
    E acesso o menu "Des. Institucional::Auto-Avaliação::Questionários"
    Então vejo a página "Questionários"
    E vejo o botão "Adicionar Questionário"
    Quando clico no botão "Adicionar Questionário"
    Então vejo a página "Adicionar Questionário"
    E vejo os seguintes campos no formulário
      | Campo           | Tipo                   |
      | Descrição       | Texto                  |
      | Público         | Lista                  |
      | Ano             | Texto                  |
      | Data de Início  | Data                  |
      | Data de Término | Data                  |
      | Dicionário      | Textarea               |
      | Campi           | FilteredSelectMultiple |
      | Categoria       | Autocomplete           |
      | Ordem           | Texto                  |
    E vejo o botão "Salvar"
    Quando preencho o formulário com os dados
      | Campo           | Tipo                   | Valor                                                       |
      | Descrição       | Texto                  | Novo Questionário                                           |
      | Público         | Lista                  | Técnicos                                                    |
      | Ano             | Texto                  |                                                        2020 |
      | Data de Início  | Data                  | 01/01/2020                                                  |
      | Data de Término | Data                  | 01/06/2020                                                  |
      | Dicionário      | Textarea               | descrição sobre o questionário                              |
      | Campi           | FilteredSelectMultiple | CZN                                                         |
      | Categoria       | Autocomplete           | ORGANIZAÇÃO, GESTÃO, PLANEJAMENTO E AVALIAÇÃO INSTITUCIONAL |
      | Ordem           | Texto                  |                                                           1 |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Questionário cadastrado com sucesso."
