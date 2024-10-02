# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro de Perguntas de Marcador Alimentar
  Permite o cadastro de perguntas de marcador alimentar que podem ser indicados nos registros de atendimentos de nutrição

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Adicionar Perguntas de Marcador Alimentar
  Cadastrar perguntas de marcadores alimentares.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Perguntas de Marcador Alimentar"
    E clico no botão "Adicionar Pergunta de Marcador Alimentar"
    E preencho o formulário com os dados
      | Campo            | Tipo  | Valor         |
      | Pergunta         | Texto | Nova Pergunta |
      | Tipo de Resposta | Lista | Única Escolha |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Editar Perguntas de Marcador Alimentar
  Editar pergunta de marcador alimentar existente.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Perguntas de Marcador Alimentar"
    E olho para a listagem
    E olho a linha "Nova Pergunta"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo            | Tipo  | Valor         |
      | Pergunta         | Texto | Nova Pergunta |
      | Tipo de Resposta | Lista | Única Escolha |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."

  @do_document
  Cenário: Visualizar Perguntas de Marcador Alimentar
  Listar perguntas de marcadores alimentares cadastradas.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Perguntas de Marcador Alimentar"
    Então vejo a página "Perguntas de Marcador Alimentar"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  @do_document
  Cenário: Buscar Perguntas de Marcador Alimentar
  Buscar perguntas de marcador alimentar.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Perguntas de Marcador Alimentar"
    E preencho o formulário com os dados
      | Campo | Tipo  | Valor         |
      | Texto | Texto | Nova Pergunta |
    E clico no botão "Filtrar"
    Então vejo a linha "Nova Pergunta"


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"

