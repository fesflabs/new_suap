# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastros de Procedimentos Multidisciplinares
  Permite o cadastro de procedimentos que podem ser indicados nos atendimentos multidisciplinares

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Adicionar Procedimento Multidisciplinar
  Cadastrar novos procedimentos multidisciplinares.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Procedimentos Multidisciplinares"
    E clico no botão "Adicionar Procedimento Multidisciplinar"
    E preencho o formulário com os dados
      | Campo       | Tipo  | Valor                              |
      | Denominação | Texto | Novo Procedimento Multidisciplinar |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Procedimento Multidisciplinar
  Editar procedimento multidisciplinar existente.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Procedimentos Multidisciplinares"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo       | Tipo  | Valor                              |
      | Denominação | Texto | Novo Procedimento Multidisciplinar |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."


  @do_document
  Cenário: Visualizar Procedimento Multidisciplinar
  Listar procedimentos multidisciplinares cadastrados.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Procedimentos Multidisciplinares"
    Então vejo a página "Procedimentos Multidisciplinares"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"

