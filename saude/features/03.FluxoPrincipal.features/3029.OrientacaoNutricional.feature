# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastros de Orientação Nutricional
  Permite o cadastro de orientações nutricionais que podem ser indicados nos registros de atendimentos de nutrição

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    E as seguintes orientacoes nutricionais
      | Titulo       | Descrição              |
      | Orientação A | Descrição orientação A |
      | Orientação B | Descrição orientação B |
      | Orientação C | Descrição orientação C |
      | Orientação D | Descrição orientação D |
      | Orientação E | Descrição orientação E |
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Adicionar Orientações Nutricionais
  Cadastrar orientações nutricionais.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Orientação Nutricional"
    E clico no botão "Adicionar Orientação Nutricional"
    E preencho o formulário com os dados
      | Campo     | Tipo       | Valor                       |
      | Título    | Texto      | Nova Orientação Nutricional |
      | Descrição | Texto Rico | Nova Orientação Nutricional |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Orientações Nutricionais
  Editar orientação nutricional existente.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Orientação Nutricional"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo  | Tipo  | Valor                       |
      | Título | Texto | Nova Orientação Nutricional |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."

  @do_document
  Cenário: Visualizar Orientações Nutricionais
  Listar orientações nutricionais cadastradas.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Cadastros::Nutrição::Orientação Nutricional"
    Então vejo a página "Orientações Nutricionais"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela



  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"

