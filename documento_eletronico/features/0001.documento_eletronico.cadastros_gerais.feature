# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastros Básicos

  Cenário: Configuração inicial para execução dos cenários documento eletronico
    Dado os cadastros básicos do documento eletrônico
    Dado acesso a página "/"
    Quando realizo o login com o usuário "200001" e senha "abcd"

  @do_document
  Cenário: Cadastrar Classificação
  O cadastro de uma classificação ocorre para permitir a criação do documento eletrônico. Ação executada pelo perfil Gerente Sistêmico de Documento Eletrônico.
    Quando pesquiso por "Classificações" e acesso o menu "Documentos/Processos::Documentos Eletrônicos::Cadastros::Classificações"
    E clico no botão "Adicionar Classificação"
    E preencho o formulário com os dados
      | Campo                                    | Tipo     | Valor  |
      | Código                                   | texto    | 1000   |
      | Descrição                                | textarea | Outros |
      | Suficiente para classificar um processo? | checkbox | True   |
      | Ativo                                    | checkbox | True   |
      | Migrado                                  | checkbox | True   |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Cadastrar Tipo de Documento Interno
  O cadastro de um tipo de documento interno ocorre para permitir a criação do documento eletrônico e dos modelos de documento. Ação executada pelo perfil Gerente Sistêmico de Documento Eletrônico.
    Quando pesquiso por "Tipos de Documentos Internos" e acesso o menu "Documentos/Processos::Documentos Eletrônicos::Cadastros::Tipos de Documentos Internos"
    E clico no botão "Adicionar Tipo de Documento Interno"
    E preencho o formulário com os dados
      | Campo            | Tipo       | Valor             |
      | Descrição        | texto      | Documento Interno |
      | Sigla            | texto      | DOCINT            |
      | Ativo            | checkbox   | True              |
      | Cabecalho padrao | texto rico | IFRN              |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Clonar Tipo de Documento Interno
  O clone de um tipo de documento interno ocorre para facilitar a criação de novos tipos de maneira prática. Ação executada pelo perfil Gerente Sistêmico de Documento Eletrônico.
    Quando acesso o menu "Documentos/Processos::Documentos Eletrônicos::Cadastros::Tipos de Documentos Internos"
    E olho para a listagem
    E olho a linha "Documento Interno"
    E clico no botão "Clonar"
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."

  @do_document
  Cenário: Cadastrar Tipo de Documento Externo
  O cadastro de um tipo de documento externo ocorre para permitir a criação do documento eletrônico e dos modelos de documento. Ação executada pelo perfil Gerente Sistêmico de Documento Eletrônico.
    Quando acesso o menu "Documentos/Processos::Documentos Eletrônicos::Cadastros::Tipos de Documentos Externos"
    E clico no botão "Adicionar Tipo de Documento Externo"
    E preencho o formulário com os dados
      | Campo     | Tipo     | Valor             |
      | Descrição | texto    | Documento Externo |
      | Sigla     | texto    | DOCEXT            |
      | Ativo     | checkbox | True              |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Cadastrar Tipo de Vínculo de Documento
  O cadastro de um tipo de vínculo de documento ocorre para realizar vinculação entre dois documentos distintos. Ação executada pelo perfil Gerente Sistêmico de Documento Eletrônico.
    Quando acesso o menu "Documentos/Processos::Documentos Eletrônicos::Cadastros::Tipos de Vínculos entre Documentos"
    E clico no botão "Adicionar Tipo de Vínculo de Documento"
    E preencho o formulário com os dados
      | Campo                    | Tipo  | Valor                  |
      | Descrição                | texto | Prorrogação            |
      | Descrição na Voz Ativa   | texto | prorroga o(a)          |
      | Descrição na Voz Passiva | texto | foi prorrogado pelo(a) |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Cadastrar Tipos de Conferência
  O cadastro de um tipo de conferência ocorre para explicar como se deu a validação de um documento (geralmente externo). Ação executada pelo perfil Gerente Sistêmico de Documento Eletrônico.
    Quando acesso o menu "Documentos/Processos::Documentos Eletrônicos::Cadastros::Tipos Conferência"
    E clico no botão "Adicionar Tipo de Conferência"
    E preencho o formulário com os dados
      | Campo     | Tipo  | Valor |
      | Descrição | texto | Outro |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Cadastrar Hipóteses Legais
  O cadastro de uma hipótese legal ocorre para justificar a restrição de acesso a um determinado documento. Ação executada pelo perfil Gerente Sistêmico de Documento Eletrônico.
    Quando acesso o menu "Documentos/Processos::Documentos Eletrônicos::Cadastros::Hipóteses Legais"
    E clico no botão "Adicionar Hipótese Legal"
    E preencho o formulário com os dados
      | Campo           | Tipo  | Valor                               |
      | Nível de Acesso | lista | Sigiloso                            |
      | Descrição       | texto | Outro                               |
      | Base Legal      | texto | Art. 26 $ 5o, da Lei no 10.180/2001 |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Cadastrar Modelos de Documentos
  O cadastro de um modelo de documento ocorre para ter um corpo já previamente preenchido parcialmente. Serve para agilizar a criação de um documento, além de categorizá-lo. Ação executada pelo perfil Gerente Sistêmico de Documento Eletrônico.
    Quando acesso o menu "Documentos/Processos::Documentos Eletrônicos::Cadastros::Modelos"
    E clico no botão "Adicionar Modelo de Documento"
    E preencho o formulário com os dados
      | Campo                  | Tipo         | Valor             |
      | Tipo do Documento      | autocomplete | Documento Interno |
      | Descrição              | texto        | Outro             |
      | Sigiloso?              | checkbox     | True              |
      | Restrito?              | checkbox     | True              |
      | Público?               | checkbox     | True              |
      | Nível de Acesso Padrão | lista        | Público           |
      | Ativo                  | checkbox     | True              |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


