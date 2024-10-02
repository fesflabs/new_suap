# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro de Avaliação Gastrointestinal
  Permite o cadastro de avaliações gastrointestinais que podem ser indicados nos registros de atendimentos de nutrição

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Adicionar Avaliações Gastrointestinais
  Cadastrar novas avaliações gastrointestinais
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Avaliação Gastrointestinal"
    E clico no botão "Adicionar Avaliação Gastrointestinal"
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor                            |
      | Descrição | Texto | Nova Avaliação Gastrointestinais |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Avaliações Gastrointestinais
  Editar avaliação gastrointestinal existente.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Avaliação Gastrointestinal"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor                            |
      | Descrição | Texto | Nova Avaliação Gastrointestinais |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."


  @do_document
  Cenário: Visualizar Avaliações Gastrointestinais
  Listar avaliações gastrointestinais cadastradas.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Avaliação Gastrointestinal"
    Então vejo a página "Avaliações Gastrointestinais"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela

  @do_document
  Cenário:  Buscar Avaliações Gastrointestinais
  Buscar avaliações gastrointestinais cadastradas.
    Dado  acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Avaliação Gastrointestinal"
    E preencho o formulário com os dados
      | Campo | Tipo  | Valor                        |
      | Texto | Texto | Nova Avaliação Gastrointestinais |
    E clico no botão "Filtrar"
    Então vejo a linha "Nova Avaliação Gastrointestinais"


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"

