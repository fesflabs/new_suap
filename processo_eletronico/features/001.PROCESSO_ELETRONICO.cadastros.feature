# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Cadastros Básicos
    Cadastros básicos do módulo de processos eletrônicos

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado acesso a página "/"
    Quando realizo o login com o usuário "admin" e senha "abc"

  @do_document
  Cenario: Adicionar Tipos de Processo
    Dado acesso a página "/"
    Quando acesso o menu "Documentos/Processos::Processos Eletrônicos::Cadastros::Tipos de Processos"
    E clico no botão "Adicionar Tipo de Processo"
    E preencho o formulário com os dados
        | Campo                   | Tipo         | Valor                    |
        | Nome                    | Texto        | Tipo de Processo X       |
        | Nível de Acesso Padrão  | Lista        | Público                  |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso"

  @do_document
  Cenario: Adicionar Modelos de Despacho
    Dado acesso a página "/"
    Quando acesso o menu "Documentos/Processos::Processos Eletrônicos::Cadastros::Modelos de Despacho"
    E clico no botão "Adicionar Modelo de Despacho"
    E preencho o formulário com os dados
      | Campo     | Tipo     | Valor                        |
      | Cabeçalho | Textarea | Cabeçalho Modelo de Despacho |
      | Rodapé    | Textarea | Cabeçalho Modelo de Despacho |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso"

  @do_document
  Cenario: Adicionar Modelos de Parecer
    Dado acesso a página "/"
    Quando acesso o menu "Documentos/Processos::Processos Eletrônicos::Cadastros::Modelos de Parecer"
    E clico no botão "Adicionar Modelo de Parecer"
    E preencho o formulário com os dados
      | Campo     | Tipo     | Valor                       |
      | Cabeçalho | Textarea | Cabeçalho Modelo de Parecer |
      | Rodapé    | Textarea | Cabeçalho Modelo de Parecer |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso"

  @do_document
  Cenario: Adicionar Configurações do Trâmite do Processo
    Dado acesso a página "/"
    Quando acesso o menu "Documentos/Processos::Processos Eletrônicos::Cadastros::Configurações do Trâmite do Requerimento"
    E clico no botão "Adicionar Configuração do Trâmite do Processo"
    E clico no botão "Buscar"
    E seleciono o item "Tipo de Processo X" da lista
    E clico no botão "Confirmar"
    E preencho o formulário com os dados
      | Campo                       | Tipo         | Valor                          |
      | Origem do interessado       | Autocomplete | A0                             |
      | Destino do primeiro trâmite | Radio        | Buscar usando o Autocompletar |
      | Setor de Destino            | Autocomplete | A0                             |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso"

  Cenario: Adicionar Hipóteses Legais
    Dado acesso a página "/"
    Quando acesso o menu "Documentos/Processos::Documentos Eletrônicos::Cadastros::Hipóteses Legais"
    E clico no botão "Adicionar Hipótese Legal"
    E preencho o formulário com os dados
      | Campo           | Tipo  | Valor               |
      | Nível de Acesso | Lista | Restrito            |
      | Descrição       | texto | Informação Restrita |
      | Base Legal      | texto | Informação Restrita |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso"
