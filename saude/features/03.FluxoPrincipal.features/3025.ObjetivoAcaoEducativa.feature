# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastros de Objetivos de Ações Educativas
  Permite o cadastro de objetivos que podem ser indicados nos registros de ações educativas

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Adicionar Objetivo da Ação Educativa
  Cadastrar novos objetivos de ação educativa.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Planejamento de Ações Educativas::Objetivos"
    E clico no botão "Adicionar Objetivo da Ação Educativa"
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor                           |
      | Descrição | Texto | Novo Objetivo de Ação Educativa |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Editar Objetivo da Ação Educativa
  Editar objetivo de ação educativa existente.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Planejamento de Ações Educativas::Objetivos"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor                           |
      | Descrição | Texto | Novo Objetivo de Ação Educativa |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."


  @do_document
  Cenário: Visualizar Objetivo da Ação Educativa
  Listar objetivos de ações educativas cadastrados.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Planejamento de Ações Educativas::Objetivos"
    Então vejo a página "Objetivos da Ação Educativa"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  @do_document
  Cenário:  Buscar Objetivo da Ação Educativa
  Buscar objetivos de ações educativas cadastrados.
    Dado  acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Planejamento de Ações Educativas::Objetivos"
    E preencho o formulário com os dados
      | Campo | Tipo  | Valor                           |
      | Texto | Texto | Novo Objetivo de Ação Educativa |
    E clico no botão "Filtrar"
    Então vejo a linha "Novo Objetivo de Ação Educativa"


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"

