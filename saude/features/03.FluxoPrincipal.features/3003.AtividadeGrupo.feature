# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Atividades em Grupo
  Permite o registro das atividades em grupo

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    E os seguintes tipos de atividades em grupo
    E os seguintes campi
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Adicionar Atividade em Grupo
  Cadastro de atividades em grupo.
  Ação executada pelo Coordenador de Saúde Sistêmico.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Atividades em Grupo"
    E clico no botão "Adicionar Atividade em Grupo"
    E preencho o formulário com os dados
      | Campo                    | Tipo                  | Valor              |
      | Nome do Evento/Atividade | Texto                 | Atividade Em Grupo |
      | Tipo                     | Autocomplete          | Reunião            |
      | Tema                     | Texto                 | Tema - Reunião     |
      | Número de Participantes  | Texto                 | 1                  |
      | Campus                   | Autocomplete          | CC                 |
      | Recurso Necessário       | Textarea              | Nenhum Recurso     |
      | Data de Início           | Data              | 29/01/2019         |
      | Data de Término          | Data              | 29/01/2019         |
      | Responsáveis             | autocomplete multiplo | 111001             |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Editar Atividade em Grupo
  Edição das atividades em grupo.
  Ação executada pelo Coordenador de Saúde Sistêmico.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Atividades em Grupo"
    E clico no ícone de edição
    E preencho o formulário com os dados
      | Campo                    | Tipo         | Valor              |
      | Nome do Evento/Atividade | Texto        | Atividade Em Grupo |
      | Tipo                     | Autocomplete | Reunião            |
      | Tema                     | Texto        | Tema - Reunião     |
      | Número de Participantes  | Texto        | 1                  |
      | Recurso Necessário       | Textarea     | Nenhum Recurso     |
      | Data de Início           | Data     | 29/01/2019         |
      | Data de Término          | Data     | 29/01/2019         |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."


  @do_document
  Cenário: Visualizar Atividade em Grupo
  Visualizar a lista de atividades em grupo cadastradas.
  Ação executada pelo Coordenador de Saúde Sistêmico.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Atividades em Grupo"
    Então vejo a página "Atividades em Grupo"
    Quando olho para a tabela
    Então vejo mais de 0 resultados na tabela


  @do_document
  Cenário: Buscar Atividades em Grupo
  Consultar dados sobre as atividades em grupo existentes.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Atividades em Grupo"
    E preencho o formulário com os dados
      | Campo  | Tipo         | Valor   |
      | Tipo   | Autocomplete | Reunião |
    Então vejo mais de 0 resultados na tabela


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"