# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Sugestão de Melhoria


  @do_document
  Cenário: Adiciona sugestão de melhoria
    Dado acesso a página "/"
    Quando realizo o login com o usuário "105004" e senha "abcd"
    E acesso o menu "Tec. da Informação::Desenvolvimento::Sugestões de Melhorias"
    Então vejo a página "Sugestões de Melhorias para o SUAP"
    Quando clico no link "Tag Especial"
    Então vejo a página "Sugestões de Melhorias para Tag Especial (Tecnologia da Informação)"
    Quando clico no link "Adicionar Sugestão"
    Então vejo a página "Adicionar Sugestão de Melhoria"
    Quando preencho o formulário com os dados
      | Campo        | Tipo      | Valor                                                    |
      | Título       | Texto     | Melhoria Tag Especial                                    |
      | Descrição    | Textarea  | Sugiro alterar a funcionalidad nos seguintes aspectos... |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Sugestão de Melhoria salva com sucesso."
    Quando acesso o menu "Sair"

  @do_document
  Cenário: Concordar com sugestão de melhoria
    Dado acesso a página "/"
    Quando realizo o login com o usuário "105005" e senha "abcd"
    E acesso o menu "Tec. da Informação::Desenvolvimento::Sugestões de Melhorias"
    E clico no link "Tag Especial"
    Então vejo a página "Sugestões de Melhorias para Tag Especial (Tecnologia da Informação)"
    Quando clico no botão "Concordar com a sugestão"
    Então vejo mensagem de sucesso "Voto cadastrado com sucesso."
    Quando acesso o menu "Sair"

  @do_document
  Cenário: Criar demanda a partir da sugestão de melhoria
    Dado acesso a página "/"
    Quando realizo o login com o usuário "105001" e senha "abcd"
    E acesso o menu "Tec. da Informação::Desenvolvimento::Sugestões de Melhorias"
    E clico no botão "Visualizar Todas"
    E clico no ícone de exibição
    E clico no botão "Atribuir-se como Responsável"
    Quando clico no botão "Editar"
    E preencho o formulário com os dados
      | Campo        | Tipo      | Valor    |
      | Situação     |   Lista   | Deferida |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Sugestão de Melhoria salva com sucesso."
    Quando clico no botão "Gerar Demanda"
    Então vejo mensagem de sucesso "Demanda gerada com sucesso."
