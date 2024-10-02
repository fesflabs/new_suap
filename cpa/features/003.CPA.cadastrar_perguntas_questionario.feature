# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Cadastrar Perguntas do Questionário

  @do_document
  Cenário: Cadastrar Perguntas do Questionário CPA
    Ação executada pelo membro do grupo cpa_gerente.

    Dado acesso a página "/"
    Quando realizo o login com o usuário "802021" e senha "abcd"
    E acesso o menu "Des. Institucional::Auto-Avaliação::Questionários"
    Então vejo a página "Questionários"
    Quando clico no ícone de exibição
    Então vejo a página "Avaliação Institucional"
    E vejo o botão "Adicionar Pergunta"
    Quando clico no botão "Adicionar Pergunta"
    E olho para o popup
    Então vejo a página "Adicionar Pergunta"
    E vejo os seguintes campos no formulário
      | Campo         | Tipo     |
      | Identificador | Texto    |
      | Texto         | Textarea |
      | Objetiva      | checkbox |
      | Ordem         | Texto    |
    E vejo o botão "Salvar"
    Quando preencho o formulário com os dados
      | Campo         | Tipo     | Valor                          |
      | Identificador | Texto    | Pergunta 1                     |
      | Texto         | Textarea | Descrição da primeira pergunta |
      | Objetiva      | checkbox | desmarcar                      |
      | Ordem         | Texto    |                              1 |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Pergunta adicionada com sucesso."
