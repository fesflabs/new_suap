# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro de Tipos de Atividade em Grupo
  Permite o cadastro de tipos de atividade que podem ser indicados nos registros de atividades em grupo

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Adicionar Tipos de Atividade em Grupo
  Cadastrar novos tipos de atividades em grupo.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Tipo de Atividade em Grupo"
    E clico no botão "Adicionar Tipo de Atividade em Grupo"
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor                           |
      | Descrição | Texto | Novo Tipo de Atividade em Grupo |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Tipos de Atividade em Grupo
  Editar tipos de atividades em grupo existentes.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Tipo de Atividade em Grupo"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor                           |
      | Descrição | Texto | Novo Tipo de Atividade em Grupo |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."


  @do_document
  Cenário: Visualizar Tipos de Atividade em Grupo
  Listar tipos de atividades em grupo cadastrados.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Tipo de Atividade em Grupo"
    Então vejo a página "Tipos de Atividade em Grupo"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"

