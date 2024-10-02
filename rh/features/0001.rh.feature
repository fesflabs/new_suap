# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Cadastros Básicos Gestão de Pessoas
  Os cadastros básicos do módulo gestão de pessoas são usados para todo o SUAP.

  Cenário: Adicionando os usuários necessários para os testes RH
    Dado os seguintes usuários
      | Nome               | Matrícula      | Setor | Lotação | Email                         | CPF            | Senha | Grupo                                       |
      | Coord_RH Sistemico | 9999100        | CZN   | CZN     | coordrhsistemico@ifrn.edu.br  | 619.993.140-85 | abcd  | Coordenador de Gestão de Pessoas Sistêmico  |

    E os dados basicos cadastrados do rh


  @do_document
  Cenário: Cadastro de Instituições

    Dado acesso a página "/"
    Quando realizo o login com o usuário "9999100" e senha "abcd"
    E acesso o menu "Gestão de Pessoas::Cadastros::Instituições"
    Então vejo a página "Instituições"
    Quando clico no botão "Adicionar Instituição"
    Então vejo a página "Adicionar Instituição"
    Quando preencho o formulário com os dados
      | Campo               | Tipo            | Valor           |
      | Instituição         | Texto           | Instituição XXX |
      | Unidade Gestora     | Texto           | 222222          |
      | UASG                | Texto           | 222222          |

    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Cadastro de Funções
    Em geral as funções são importadas do SIAPE/SIGEPE, no entanto substituições de chefias e/ou funções que não serão
    gerenciadas pelo SIAPE podem ser adicionados por essa funcionalidade

    Quando acesso o menu "Gestão de Pessoas::Cadastros::Funções"
    Então vejo a página "Funções"
    Quando clico no botão "Adicionar Função"
    Então vejo a página "Adicionar Função"
    Quando preencho o formulário com os dados
      | Campo               | Tipo            | Valor                 |
      | Codigo              | Texto           | SUB-CHEFIA            |
      | Nome                | Texto           | SUB-CHEFIA|
      | Função SUAP         | checkbox        | marcar                |
      | Função SIAPE        | checkbox        | desmarcar             |

    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


   @do_document
  Cenário: Cadastro de Histórico de Funções
    Em geral as funções dos servidores são importadas do SIAPE/SIGEPE, no entanto substituições de chefias e/ou funções que não serão
    gerenciadas pelo SIAPE podem ser adicionados por essa funcionalidade.

    Quando acesso o menu "Gestão de Pessoas::Administração de Pessoal::Cadastros Auxiliares::Histórico de Funções dos Servidores"
    Então vejo a página "Histórico de Funções do Servidor"
    Quando clico no botão "Adicionar Histórico de Função do Servidor"
    Então vejo a página "Adicionar Histórico de Função do Servidor"
    Quando preencho o formulário com os dados
      | Campo                   | Tipo            | Valor                      |
      | Servidor                | Autocomplete    | 9999100                    |
      | Data Início na Função   | Data            | 20/07/2020                 |
      | Função                  | Lista           | SUB-CHEFIA                |
      | Setor SIAPE             | Autocomplete    | CZN                        |
      | Setor SUAP              | Autocomplete    | CZN                        |
      | Nome Amigável da Função | Texto           | Coordenador X - substituto |

    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


# Histórico Setores Servidor	Adicionar	Modificar
# Histórico de Funções do Servidor	Adicionar	Modificar
# Históricos de Jornadas dos Setores