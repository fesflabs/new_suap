# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro e Configuração do Edital

      Cenário: Adicionando os usuários necessários para os testes PROJETOS
          Dado os dados básicos para a extensão
            E  os seguintes usuários
                | Nome                   | Matrícula      | Setor    | Lotação  | Email                      | CPF            | Senha | Grupo                         |
                | Gerente de Extensão    | 110001         | CZN      | CZN      | gerente@ifrn.edu.br        | 645.433.195-40 | abcd  | Gerente Sistêmico de Extensão |
                | CoordExtensao          | 110002         | DIAC/CZN | DIAC/CZN | coord_extensao@ifrn.edu.br | 188.135.291-98 | abcd  | Coordenador de Extensão       |
                | CoordProj              | 110003         | DIAC/CZN | DIAC/CZN | coord_proj@ifrn.edu.br     | 921.728.444-03 | abcd  | Servidor                      |
                | Servidor Extensão A    | 110004         | DIAC/CZN | DIAC/CZN | servidor_a@ifrn.edu.br     | 569.522.338-57 | abcd  | Servidor                      |
                | Avaliador Extensão A   | 110005         | DIAC/CZN | DIAC/CZN | avaliador1_a@ifrn.edu.br   | 232.607.644-37 | abcd  | Servidor                      |
                | Avaliador Extensão B   | 110006         | DIAC/CZN | DIAC/CZN | avaliador2_b@ifrn.edu.br   | 568.288.693-38 | abcd  | Servidor                      |
                | Aluno Extensão         | 20191101011101 | DIAC/CZN | DIAC/CZN | aluno1@ifrn.edu.br         | 783.313.990-48 | abcd  | Aluno                         |


   Esquema do Cenário: Verifica a visibilidade do menu Projetos e da adição do Edital pelo <Papel>
        Dado acesso a página "/"
        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
        Então vejo o item de menu "Extensão::Projetos::Editais::Gerenciar Editais"
        Quando acesso a página "/admin/projetos/edital/"
        Então vejo a página "Editais"
        E vejo o botão "Adicionar Edital"
        Quando acesso o menu "Sair"
          Exemplos:
              | Papel  |
              | 110001 |

      @do_document
      Cenário: Cadastro do Edital
      Cadastro do edital para seleção de projetos de extensão.
      Ação executada pelo Gerente Sistêmico de Extensão ou Coordenador de Extensão.
          Dado acesso a página "/"
        Quando realizo o login com o usuário "110001" e senha "abcd"
             E acesso o menu "Extensão::Projetos::Editais::Gerenciar Editais"
         Então vejo a página "Editais"
             E vejo o botão "Adicionar Edital"
        Quando clico no botão "Adicionar Edital"
         Então vejo a página "Adicionar Edital"
             E vejo os seguintes campos no formulário
               | Campo                          | Tipo     |
               | Título                         | Texto    |
               | Descrição                      | TextArea |
               | Tipo do Fomento                | Lista    |
               | Tipo do Edital                 | Lista    |
               | Forma de Seleção               | Lista    |
               | Edital de Campus               | Checkbox |
               | Início das Inscrições          | Data    |
               | Fim das Inscrições             | Data    |
               | Início da Pré-Seleção          | Data    |
               | Início da Seleção              | Data    |
               | Fim da Seleção                 | Data    |
               | Divulgação da Seleção          | Data    |
               | Participação de Aluno Obrigatória | Checkbox |
               | Participação de Servidor Obrigatória | Checkbox |
               | Valor Financiado por Projeto   | Texto    |

             E vejo o botão "Salvar"

        Quando preencho o formulário com os dados
               | Campo                               | Tipo     | Valor                    |
               | Título                              | Texto    | Nome do edital           |
               | Descrição                           | TextArea | Descrição do Edital      |
               | Tipo do Fomento                     | Lista    | Interno                  |
               | Tipo do Edital                      | Lista    | Extensão                 |
               | Forma de Seleção                    | Lista    | Campus                   |
               | Edital de Campus                    | Checkbox | marcar                   |
               | Início das Inscrições               | Data    | 01/01/2018               |
               | Fim das Inscrições                  | Data    | 10/01/2018               |
               | Início da Pré-Seleção               | Data    | 11/01/2018               |
               | Início da Seleção                   | Data    | 15/01/2018               |
               | Fim da Seleção                      | Data    | 17/01/2018               |
               | Divulgação da Seleção               | Data    | 18/01/2018               |
               | Participação de Aluno Obrigatória   | Checkbox | marcar                   |
               | Participação de Servidor Obrigatória | Checkbox | marcar                  |
               | Valor Financiado por Projeto        | Texto    | 10.000,00                |



             E clico no botão "Salvar"

         Então vejo mensagem de sucesso "Edital cadastrado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"
      @do_document
      Cenário: Cadastro do Plano de Oferta por Campus
      O Plano de Oferta define a abrangência do edital. Apenas servidores dos campi inseridos no Plano de Oferta poderão submeter projetos.
      Ação executada pelo Gerente Sistêmico de Extensão ou Coordenador de Extensão.
          Dado acesso a página "/"
        Quando realizo o login com o usuário "110001" e senha "abcd"
             E acesso o menu "Extensão::Projetos::Editais::Gerenciar Editais"
         Então vejo a página "Editais"
        Quando olho para a listagem
             E olho a linha "Nome do edital"
             E clico no ícone de exibição
         Então vejo a página "Nome do edital - Edital de Extensão"
        Quando clico na aba "Plano de Oferta por Campus"
         Então vejo o botão "Adicionar Oferta"
        Quando clico no botão "Adicionar Oferta"
           E olho para o popup
           Então vejo os seguintes campos no formulário
               | Campo                          | Tipo  |
               | Campus                         | Autocomplete |
               | Pré-Selecionados               | Texto |
               | Selecionados                   | Texto |
           E vejo o botão "Salvar"
        Quando preencho o formulário com os dados
            | Campo            | Tipo         | Valor |
            | Campus           | Autocomplete | CZN   |
            | Pré-Selecionados | Texto        | 5     |
            | Selecionados     | Texto        | 3     |
             E clico no botão "Salvar"
         Então vejo mensagem de sucesso "Oferta adicionada com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"
      @do_document
      Cenário: Cadastro das Fontes de Recurso do Edital
      O valor informado deverá ser o máximo que cada projeto aprovado poderá gastar na respectiva despesa(rubrica).
      Este valor servirá como base para o coordenador do projeto definir a memória de cálculo e o plano de desembolso.
      Ação executada pelo Gerente Sistêmico de Extensão ou Coordenador de Extensão.
          Dado acesso a página "/"
        Quando realizo o login com o usuário "110001" e senha "abcd"
             E acesso o menu "Extensão::Projetos::Editais::Gerenciar Editais"
         Então vejo a página "Editais"
        Quando olho para a listagem
             E olho a linha "Nome do edital"
             E clico no ícone de exibição
         Então vejo a página "Nome do edital - Edital de Extensão"
        Quando clico na aba "Fonte de Recursos"
         Então vejo o botão "Adicionar Recurso"
        Quando clico no botão "Adicionar Recurso"
             E olho para o popup
             Então vejo os seguintes campos no formulário
                 | Campo                          | Tipo     |
                 | Origem                         | Lista    |
                 | Valor disponível (R$)          | Texto    |
                 | Despesa                        | Autocomplete    |
                 E vejo o botão "Salvar"
          Quando preencho o formulário com os dados
               | Campo                          | Tipo         | Valor                                    |
               | Origem                         | Lista        | PROEX                                    |
               | Valor disponível (R$)          | Texto        | 10.000,00                                |
               | Despesa                        | Autocomplete | Auxílio Financeiro a Estudantes   |
             E clico no botão "Salvar"

         Então vejo mensagem de sucesso "Recurso adicionado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"


      @do_document
      Cenário: Cadastro dos Critérios de Avaliação do Edital
      Definição dos critérios que serão utilizados para avaliar os projetos submetidos.
      Ação executada pelo Gerente Sistêmico de Extensão ou Coordenador de Extensão.
          Dado acesso a página "/"
             Quando realizo o login com o usuário "110001" e senha "abcd"
               E acesso o menu "Extensão::Projetos::Editais::Gerenciar Editais"
               Então vejo a página "Editais"
          Quando olho para a listagem
               E olho a linha "Nome do edital"
               E clico no ícone de exibição
           Então vejo a página "Nome do edital - Edital de Extensão"
          Quando clico na aba "Critérios de Avaliação da Qualificação do Projeto"
           Então vejo o botão "Adicionar Critério de Avaliação"
          Quando clico no botão "Adicionar Critério de Avaliação"
              E olho para o popup
              Então vejo os seguintes campos no formulário
               | Campo                          | Tipo     |
               | Descrição                      | TextArea |
               | Pontuação Máxima               | Texto    |
               | Ordem para Desempate           | Texto    |
              E vejo o botão "Salvar"
          Quando preencho o formulário com os dados
               | Campo                          | Tipo     | Valor                   |
               | Descrição                      | TextArea | Descrição do Critério 1 |
               | Pontuação Máxima               | Texto    | 10,00                   |
               | Ordem para Desempate           | Texto    | 1                       |
             E clico no botão "Salvar"

         Então vejo mensagem de sucesso "Critério de avaliação adicionado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"

      @do_document
      Cenário: Cadastro da Comissão de Avaliação do Edital
      A comissão de avaliação deve ser formada por todos os possíveis avaliadores dos projetos submetidos.
      Durante a fase de pré-seleção dos projetos, será feita a indicação dos avaliadores de cada projeto.
      Ação executada pelo Gerente Sistêmico de Extensão ou Coordenador de Extensão.
          Dado acesso a página "/"
             Quando realizo o login com o usuário "110001" e senha "abcd"
               E acesso o menu "Extensão::Projetos::Editais::Comissão de Avaliação"
               Então vejo a página "Comissões de Avaliação"
               E vejo o botão "Adicionar Comissão de Avaliação"
          Quando clico no botão "Adicionar Comissão de Avaliação"
              Então vejo os seguintes campos no formulário
               | Campo                                 | Tipo                    |
               | Filtrar por Ano                       | Lista                   |
               | Filtrar por Edital                    | Lista                   |
               | Clonar Comissão de um Edital anterior | Checkbox                |
               | Membro                                | Autocomplete Multiplo   |



              E vejo o botão "Salvar"
          Quando preencho o formulário com os dados
              | Campo              | Tipo                  | Valor          |
              | Filtrar por Edital | Lista                 | Nome do edital |
              | Membro             | Autocomplete Multiplo | 110005         |
             E clico no botão "Salvar"
         Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"


      @do_document
      Cenário: Edição da Comissão de Avaliação do Edital
      Inclusão de mais um avaliador na comissão de avaliação do edital.
      Ação executada pelo Gerente Sistêmico de Extensão ou Coordenador de Extensão.
          Dado acesso a página "/"
             Quando realizo o login com o usuário "110001" e senha "abcd"
               E acesso o menu "Extensão::Projetos::Editais::Comissão de Avaliação"
               Então vejo a página "Comissões de Avaliação"
             Quando olho para a listagem
               E olho a linha "Nome do edital - Edital de Extensão"
               E clico no ícone de edição
          Então vejo a página "Editar Comissão do Nome do edital"

          Quando preencho o formulário com os dados
              | Campo              | Tipo                  | Valor          |
              | Filtrar por Edital | Lista                 | Nome do edital |
              | Membro             | Autocomplete Multiplo | 110006         |
             E clico no botão "Salvar"
         Então vejo mensagem de sucesso "Atualização realizada com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"
