# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro de Respostas de Perguntas de Marcador Alimentar
  Permite o cadastro de respostas para pergunta de marcadores alimentares que podem ser indicados nos registros de atendimentos de nutrição

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    E as seguintes perguntas
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Adicionar Opção de Resposta de Marcador Alimentar
  Cadastrar opções de respostas de marcadores alimentares.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Respostas de Perguntas de Marcador Alimentar"
    E clico no botão "Adicionar Opção de Resposta de Marcador Alimentar"
    E preencho o formulário com os dados
      | Campo             | Tipo         | Valor         |
      | Pergunta          | Autocomplete | Nova Pergunta |
      | Opção de Resposta | Texto        | Nova Resposta |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Opção de Resposta de Marcador Alimentar
  Editar opção de resposta para marcador alimentar existente.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Respostas de Perguntas de Marcador Alimentar"
    E olho para a listagem
    E olho a linha "Nova Pergunta"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo             | Tipo         | Valor         |
      | Pergunta          | Autocomplete | Nova Pergunta |
      | Opção de Resposta | Texto        | Nova Resposta |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."


  @do_document
  Cenário: Visualizar Opção de Resposta de Marcador Alimentar
  Listar opções de respostas de marcadores alimentares cadastrados.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Respostas de Perguntas de Marcador Alimentar"
    Então vejo a página "Opções de Resposta de Marcador Alimentar"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"

