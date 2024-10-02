# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Planejamento de Ações Educativas
  Permite o cadastro das ações educativas

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    E os seguintes anos de referencia
    E os seguintes objetivos
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Adicionar Metas da Ação Educativa
  Cadastro de metas de ação educativa.
  Ação executada pelo Coordenador de Saúde Sistêmico.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Planejamento de Ações Educativas::Metas"
    E clico no botão "Adicionar Meta da Ação Educativa"
    E preencho o formulário com os dados
      | Campo             | Tipo                  | Valor                           |
      | Ano de Referência | Autocomplete          | 2019                            |
      | Objetivos         | Autocomplete multiplo | Novo Objetivo de Ação Educativa |
      | Tipo de Indicador | Lista                 | Número de Ações                 |
      | Quantidade        | Texto                 | 2                               |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Adicionar Metas da Ação Educativa
  Cadastro de metas de ação independente.
  Ação executada pelo Coordenador de Saúde Sistêmico.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Planejamento de Ações Educativas::Metas"
    E clico no botão "Cadastrar Ação Independente"
    E preencho o formulário com os dados
      | Campo                    | Tipo     | Valor          |
      | Nome do Evento/Atividade | Texto    | Ação Educativa |
      | Recurso Necessário       | Textarea | Nenhum Recurso |
      | Data de Início           | Data     | 24/04/2019     |
      | Data de Término          | Data     | 24/04/2019     |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Ação cadastrada com sucesso."

  @do_document
  Cenário: Editar Atividade em Grupo
  Edição de de atividades complementares.
  Ação executada pelo Coordenador de Saúde Sistêmico.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Planejamento de Ações Educativas::Metas"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo             | Tipo                  | Valor                           |
      | Ano de Referência | Autocomplete          | 2019                            |
      | Tipo de Indicador | Lista                 | Número de Ações                 |
      | Quantidade        | Texto                 | 2                               |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."

  @do_document
  Cenário: Visualizar Metas da Ação Educativa
  Visualizar a lista de metas de ação educativa.
  Ação executada pelo Coordenador de Saúde Sistêmico.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Planejamento de Ações Educativas::Metas"
    Então vejo a página "Metas"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"