# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Cadastros Básicos

  Cenário: Adicionando os usuários necessários para os testes REMANEJAMENTO
    Dado os seguintes usuários
      | Nome                      | Matrícula | Setor | Lotação | Email                              | CPF            | Senha | Grupo                        |
      | Coordenador Remanejamento | 7114145   | CZN   | CZN     | coord_remanejamento@ifrn.edu.br    | 219.963.250-43 | abcd  | Coordenador de Remanejamento |
      | Servidor Remanejamento    | 7114156   | CZN   | CZN     | servidor_remanejamento@ifrn.edu.br | 674.181.420-56 | abcd  | Servidor                     |

  @do_document
  Cenário: Cadastro de Edital de Remanejamento
  Cadastro de Edital de Remanejamento.
  Ação executada por um membro do grupo Coordenador de Remanejamento.

    Dado acesso a página "/"
    Quando realizo o login com o usuário "7114145" e senha "abcd"
    E acesso o menu "Gestão de Pessoas::Desenvolvimento de Pessoal::Remanejamento::Editais"
    Então vejo a página "Editais"
    E vejo o botão "Adicionar Edital"
    Quando clico no botão "Adicionar Edital"
    Então vejo a página "Adicionar Edital"
    Quando preencho o formulário com os dados
      | Campo                               | Tipo                  | Valor                        |
      | Título                              | Texto                 | Novo Edital de Remanejamento |
      | Descrição                           | TextArea              | descricao do edital          |
      | Campi                              | FilteredSelectMultiple | CZN                          |
      | Cargos                              | Autocomplete multiplo | Cargo A                      |
      | Coordenadores                       | Autocomplete multiplo | Coordenador Remanejamento    |
      | Chave hash                          | Texto                 | asdasd                       |
      | Início dos Recursos ao Edital       | Data                  | 01/05/2020                   |
      | Fim dos Recursos ao Edital          | Data                  | 30/05/2020                   |
      | Resultado dos Recursos ao Edital    | Data                  | 31/05/2020                   |
      | Início das inscrições               | Data                  | 01/06/2020                   |
      | Fim das inscrições                  | Data                  | 15/06/2020                   |
      | Início dos recursos do resultado    | Data                  | 16/06/2020                   |
      | Fim dos recursos do resultado       | Data                  | 20/06/2020                   |
      | Resultado dos recursos ao resultado | Data                  | 21/06/2020                   |
      | Resultado Final                     | Data                  | 30/06/2020                   |

    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Cadastrar Disciplina do Remanejamento
  Ação executada por um membro do grupo Coordenador de Remanejamento.

    Quando acesso o menu "Gestão de Pessoas::Desenvolvimento de Pessoal::Remanejamento::Cadastros::Disciplinas"
    Então vejo a página "disciplinas"
    Quando clico no link "Adicionar disciplina"
    Então vejo a página "Adicionar disciplina"
    E vejo os seguintes campos no formulário
      | Campo     | Tipo         |
      | Edital    | Autocomplete |
      | Descrição | Texto        |
    E vejo o botão "Salvar"
    Quando preencho o formulário com os dados
      | Campo     | Tipo         | Valor                        |
      | Edital    | Autocomplete | Novo Edital de Remanejamento |
      | Descrição | Texto        | descricao da disciplina      |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."
