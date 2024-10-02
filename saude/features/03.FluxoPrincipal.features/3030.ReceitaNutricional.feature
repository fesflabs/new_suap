# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro de Receitas
  Permite o cadastro de receitas alimentares que podem ser indicados nos registros de atendimentos de nutrição

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Adicionar Receitas Alimentares
    Cadastrar receitas alimentares.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Receitas"
    E clico no botão "Adicionar Receita"
    E preencho o formulário com os dados
      | Campo     | Tipo       | Valor        |
      | Título    | Texto      | Nova Receita |
      | Descrição | Texto Rico | Nova Receita |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Receitas Alimentares
    Editar receita alimentar.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Receitas"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo  | Tipo  | Valor        |
      | Título | Texto | Nova Receita |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."


  @do_document
  Cenário: Visualizar Receitas Alimentares
    Listar receitas alimentares cadastradas.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Receitas"
    Então vejo a página "Receitas"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"

