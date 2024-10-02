# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro de Restrições Alimentares
  Permite o cadastro de restrições alimentares que podem ser indicados nos registros de atendimentos de nutrição

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Adicionar Restrições Alimentares
  Cadastrar novas restrições alimentares existentes.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Restrições Alimentares"
    E clico no botão "Adicionar Restrição Alimentar"
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor                        |
      | Descrição | Texto | Novas Restrições Alimentares |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Restrições Alimentares
  Editar restrição alimentar existente.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Restrições Alimentares"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor                        |
      | Descrição | Texto | Novas Restrições Alimentares |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."


  @do_document
  Cenário: Visualizar Restrições Alimentares
  Listar restrições alimentares cadastradas.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Restrições Alimentares"
    Então vejo a página "Restrições Alimentares"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  @do_document
  Cenário:  Buscar Restrições Alimentares
  Buscar restrições alimentares cadastradas.
    Dado  acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Restrições Alimentares"
    E preencho o formulário com os dados
      | Campo | Tipo  | Valor                        |
      | Texto | Texto | Novas Restrições Alimentares |
    E clico no botão "Filtrar"
    Então vejo a linha "Novas Restrições Alimentares"


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"

