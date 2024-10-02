# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro dos Motivos do Atendimento de Nutrição
  Permite o cadastro de motivos de atendimento que podem ser indicados nos registros de atendimentos de nutrição

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Adicionar Motivos do Atendimento
  Cadastrar motivos de atendimentos.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Motivo do Atendimento"
    E clico no botão "Adicionar Motivo do Atendimento"
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor              |
      | Descrição | Texto | Motivo Atendimento |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Motivos do Atendimento
  Editar motivo de atendimento existente.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Motivo do Atendimento"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor              |
      | Descrição | Texto | Motivo Atendimento |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."

  @do_document
  Cenário: Visualizar Motivos do Atendimento
  Listar motivos de atendimentos cadastrados.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Motivo do Atendimento"
    Então vejo a página "Motivos do Atendimento"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela

  @do_document
  Cenário: Buscar Motivos do Atendimento
  Buscar motivos de atendimento existentes.
    Dado  acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Motivo do Atendimento"
    E preencho o formulário com os dados
      | Campo | Tipo  | Valor              |
      | Texto | Texto | Motivo Atendimento |
    E clico no botão "Filtrar"
    Então vejo a linha "Motivo Atendimento"


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"

