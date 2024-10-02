# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro e Configuração do Edital

      Cenário: Adicionando os usuários necessários para os testes PESQUISA
          Dado os dados básicos para a pesquisa
            E  os seguintes usuários
                | Nome                 | Matrícula | Setor    | Lotação  | Email                      | CPF            | Senha | Grupo                   |
                | Diretor Pesquisa     | 108001    | CZN      | CZN      | diretor_pesq@ifrn.edu.br   | 645.433.195-40 | abcd  | Diretor de Pesquisa     |
                | Coordenador Pesquisa | 108002    | DIAC/CZN | DIAC/CZN | coord_pesquisa@ifrn.edu.br | 188.135.291-98 | abcd  | Coordenador de Pesquisa |
                | Coordenador Projeto  | 108003    | DIAC/CZN | DIAC/CZN | coord_proj@ifrn.edu.br     | 921.728.444-03 | abcd  | Servidor                |
                | Servidor Projeto     | 108004    | DIAC/CZN | DIAC/CZN | servidor_pesq@ifrn.edu.br  | 232.607.644-37 | abcd  | Servidor                |
                | Avaliador1 Pesquisa  | 108005    | DIAC/CZN | DIAC/CZN | avaliador_a@ifrn.edu.br    | 232.607.644-37 | abcd  | Servidor                |
                | Avaliador2 Pesquisa  | 108006    | DIAC/CZN | DIAC/CZN | avaliador_b@ifrn.edu.br    | 568.288.693-38 | abcd  | Servidor                |
                | Aluno do Projeto      | 20191101011081 | DIAC/CZN | DIAC/CZN | aluno2@ifrn.edu.br         | 359.221.769-00 | abcd  | Aluno                         |
                | Coordenador do Laboratório  | 108013    | DIAC/CZN | DIAC/CZN | coord_proj@ifrn.edu.br     | 921.728.444-04 | abcd  | Servidor         |
                | Membro do Laboratório     | 108014    | DIAC/CZN | DIAC/CZN | servidor_membro@ifrn.edu.br  | 232.607.644-39 | abcd  | Servidor         |
            E os usuários da pesquisa

   Esquema do Cenário: Verifica a visibilidade do menu Pesquisa e da adição do Edital pelo <Papel>
        Dado acesso a página "/"
        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
        Então vejo o item de menu "Pesquisa::Editais::Gerenciar Editais"
        Quando acesso a página "/admin/pesquisa/edital/"
        Então vejo a página "Editais"
        E vejo o botão "Adicionar Edital"
        Quando acesso o menu "Sair"
          Exemplos:
              | Papel  |
              | 108001 |

      @do_document
      Cenário: Cadastro do Edital
      Cadastro do edital para seleção de projetos de pesquisa.
      Ação executada pelo Diretor de Pesquisa ou Coordenador de Pesquisa.
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108001" e senha "abcd"
             E acesso o menu "Pesquisa::Editais::Gerenciar Editais"
         Então vejo a página "Editais"
             E vejo o botão "Adicionar Edital"
        Quando clico no botão "Adicionar Edital"
         Então vejo a página "Adicionar Edital"
             E vejo os seguintes campos no formulário
               | Campo                                         | Tipo     |
               | Título                                        | Texto    |
               | Descrição                                     | TextArea |
               | Tipo do Edital                                | Lista    |
               | Formato do Edital                             | Lista    |
               | Forma de Seleção                              | Lista    |
               | Edital de Campus                              | Checkbox |
               | Início das Inscrições                         | Data     |
               | Fim das Inscrições                            | Data     |
               | Início da Pré-Seleção                         | Data     |
               | Início da Seleção                             | Data     |
               | Fim da Seleção                                | Data     |
               | Data Limite Para Recursos                     | Data     |
               | Divulgação da Seleção                         | Texto    |
               | Coordenador pode receber bolsa                | Checkbox |
               | Coordenador com mais de uma bolsa             | Checkbox |
               | Apenas para membros de grupo de pesquisa      | Checkbox |
               | Currículo Lattes Obrigatório                  | Checkbox |
               | Titulações dos Avaliadores                    | FilteredSelectMultiple    |
               | Participação de Aluno Obrigatória             | Checkbox |
               | Participação de Servidor Obrigatória          | Checkbox |
               | Anos de consideração das Publicações          | Texto |
               | Peso da Avaliação do Coordenador (%)          | Texto |
               | Peso da Avaliação do Projeto (%)              | Texto |
               | Ponto de Corte para Aprovação de Projeto (%)  | Texto |
               | Carga Horária do Coordenador                  | Texto |
               | Termo de Compromisso do Coordenador           | TextArea |
               | Período máximo currículo desatualizado        | Texto |
               | Total de Servidores                           | Texto |
               | Total de Servidores Bolsistas                 | Texto |
               | Total de Alunos                               | Texto |
               | Total de Alunos Bolsistas                     | Texto |
             E vejo o botão "Salvar"


        Quando preencho o formulário com os dados
               | Campo                                         | Tipo     | Valor                 |
               | Título                                        | Texto    | Nome do edital |
               | Descrição                                     | TextArea | escrição do Edital  |
               | Tipo do Edital                                | Lista    | Pesquisa |
               | Formato do Edital                             | Lista    | Completo |
               | Forma de Seleção                              | Lista    | Campus |
               | Edital de Campus                              | Checkbox | marcar |
               | Início das Inscrições                         | Data     | 01/01/2018 |
               | Fim das Inscrições                            | Data     | 10/01/2018 |
               | Início da Pré-Seleção                         | Data     | 11/01/2018 |
               | Início da Seleção                             | Data     | 15/01/2018 |
               | Fim da Seleção                                | Data     | 17/01/2018 |
               | Divulgação da Seleção                         | Data     | 19/01/2018 |
               | Titulações dos Avaliadores                    | FilteredSelectMultiple    | Doutorado  |
               | Participação de Aluno Obrigatória             | Checkbox | desmarcar                   |
               | Anos de consideração das Publicações          | Texto    | 3 |
               | Peso da Avaliação do Coordenador (%)          | Texto    | 30 |
               | Peso da Avaliação do Projeto (%)              | Texto    | 70 |
               | Ponto de Corte para Aprovação de Projeto (%)  | Texto    | 50 |
               | Carga Horária do Coordenador                  | Texto    | 4 |

               | Período máximo currículo desatualizado        | Texto    | 6 |
               | Total de Servidores                           | Texto    | 5 |
               | Total de Servidores Bolsistas                 | Texto    | 3 |
               | Total de Alunos                               | Texto    | 2 |
               | Total de Alunos Bolsistas                     | Texto    | 1 |

             E clico no botão "Salvar"

         Então vejo mensagem de sucesso "Edital cadastrado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"
      @do_document
      Cenário: Cadastro do Plano de Oferta por Campus
      O Plano de Oferta define a abrangência do edital. Apenas servidores dos campi inseridos no Plano de Oferta poderão submeter projetos.
      Ação executada pelo Diretor de Pesquisa ou Coordenador de Pesquisa.
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108001" e senha "abcd"
             E acesso o menu "Pesquisa::Editais::Gerenciar Editais"
         Então vejo a página "Editais"
        Quando olho para a listagem
             E olho a linha "Nome do edital"
             E clico no ícone de exibição
         Então vejo a página "Nome do edital - Edital de Pesquisa"
             Quando clico na aba "Plano de Oferta por Campus"
            Então vejo o botão "Adicionar Oferta"
        Quando clico no botão "Adicionar Oferta"
           Então vejo os seguintes campos no formulário
               | Campo                          | Tipo                   |
               | Campi                          | FilteredSelectMultiple |
               | Bolsas de Iniciação Científica | Texto                  |
               | Bolsas para Pesquisador        | Texto                  |
           E vejo o botão "Enviar"
        Quando preencho o formulário com os dados
            | Campo                          | Tipo                   | Valor    |
            | Campi                          | FilteredSelectMultiple | CZN, CEN |
            | Bolsas de Iniciação Científica | Texto                  | 5        |
            | Bolsas para Pesquisador        | Texto                  | 3        |
             E clico no botão "Enviar"
         Então vejo mensagem de sucesso "Oferta(s) adicionada(s) com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"
      @do_document
      Cenário: Cadastro das Fontes de Recurso do Edital
      O valor informado deverá ser o máximo que cada projeto aprovado poderá gastar na respectiva despesa(rubrica).
      Este valor servirá como base para o coordenador do projeto definir a memória de cálculo e o plano de desembolso.
      Ação executada pelo Diretor de Pesquisa ou Coordenador de Pesquisa.
          Dado acesso a página "/"
             Quando realizo o login com o usuário "108001" e senha "abcd"
             E acesso o menu "Pesquisa::Editais::Gerenciar Editais"
          Então vejo a página "Editais"
          Quando olho para a listagem
             E olho a linha "Nome do edital"
             E clico no ícone de exibição
          Então vejo a página "Nome do edital - Edital de Pesquisa"
             Quando clico na aba "Fonte de Recursos"
            Então vejo o botão "Adicionar Recurso"
          Quando clico no botão "Adicionar Recurso"
             E olho para o popup
             Então vejo os seguintes campos no formulário
                 | Campo                          | Tipo         |
                 | Origem                         | Lista        |
                 | Valor disponível (R$)          | Texto        |
                 | Despesa                        | Autocomplete |
                 E vejo o botão "Salvar"
          Quando preencho o formulário com os dados
               | Campo                          | Tipo         | Valor                                    |
               | Origem                         | Lista        | PROPI                                    |
               | Valor disponível (R$)          | Texto        | 10.000,00                                |
               | Despesa                        | Autocomplete | Auxílio Financeiro a Estudantes |
             E clico no botão "Salvar"

         Então vejo mensagem de sucesso "Recurso adicionado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"


      @do_document
      Cenário: Cadastro dos Critérios de Avaliação do Edital
      Definição dos critérios que serão utilizados para avaliar os projetos submetidos.
      Ação executada pelo Diretor de Pesquisa ou Coordenador de Pesquisa.
          Dado acesso a página "/"
             Quando realizo o login com o usuário "108001" e senha "abcd"
               E acesso o menu "Pesquisa::Editais::Gerenciar Editais"
               Então vejo a página "Editais"
          Quando olho para a listagem
               E olho a linha "Nome do edital"
               E clico no ícone de exibição
              Então vejo a página "Nome do edital - Edital de Pesquisa"
               Quando clico na aba "Critérios de Avaliação da Qualificação do Projeto"
               Então vejo o botão "Adicionar Critério de Avaliação"
          Quando clico no botão "Adicionar Critério de Avaliação"
              E olho para o popup
              Então vejo os seguintes campos no formulário
               | Campo                          | Tipo     |
               | Descrição                      | TextArea |
               | Pontuação Máxima               | Texto    |

              E vejo o botão "Salvar"
          Quando preencho o formulário com os dados
               | Campo                          | Tipo     | Valor                   |
               | Descrição                      | TextArea | Descrição do Critério 1 |
               | Pontuação Máxima               | Texto    | 10,00                   |

             E clico no botão "Salvar"

         Então vejo mensagem de sucesso "Critério de avaliação adicionado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"


      @do_document
      Cenário: Cadastro da Comissão de Avaliação do Edital
      A comissão de avaliação deve ser formada por todos os possíveis avaliadores dos projetos submetidos.
      Durante a fase de pré-seleção dos projetos, será feita a indicação dos avaliadores de cada projeto.
      Ação executada pelo Diretor de Pesquisa ou Coordenador de Pesquisa.
          Dado acesso a página "/"
             Quando realizo o login com o usuário "108001" e senha "abcd"
               E acesso o menu "Pesquisa::Editais::Comissão de Avaliação"
               Então vejo a página "Comissões de Avaliação"
               E vejo o botão "Adicionar Comissão de Avaliação"
          Quando clico no botão "Adicionar Comissão de Avaliação"
               E clico no botão "Por Indicação de Nomes"
              Então vejo os seguintes campos no formulário
               | Campo                                 | Tipo                    |
               | Filtrar por Ano                       | Lista                   |
               | Filtrar por Edital                    | Lista                   |
               | Campus                                | Lista            |
               | Clonar Comissão de um Edital anterior | Checkbox                |
               | Membro                                | autocomplete multiplo   |

              E vejo o botão "Salvar"
          Quando preencho o formulário com os dados
               | Campo                                 | Tipo                  | Valor            |
               | Filtrar por Edital                    | Lista                 | Nome do edital   |
               | Campus                                | Lista          | CZN               |
               | Membro                                | autocomplete multiplo | Avaliador1 Pesquisa |
             E clico no botão "Salvar"
         Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"


      @do_document
      Cenário: Edição da Comissão de Avaliação do Edital
      Inclusão de mais um avaliador na comissão de avaliação do edital.
      Ação executada pelo Diretor de Pesquisa ou Coordenador de Pesquisa.
          Dado acesso a página "/"
             Quando realizo o login com o usuário "108001" e senha "abcd"
               E acesso o menu "Pesquisa::Editais::Comissão de Avaliação"
               Então vejo a página "Comissões de Avaliação"
             Quando olho para a listagem
               E olho a linha "Nome do edital - Edital de Pesquisa"
               E clico no ícone de edição
          Então vejo a página "Editar Comissão do Nome do edital"

          Quando preencho o formulário com os dados
               | Campo                                 | Tipo                  | Valor            |
               | Filtrar por Edital                    | Lista                 | Nome do edital   |
               | Membro                                | Autocomplete Multiplo | Avaliador2 Pesquisa |
             E clico no botão "Salvar"
         Então vejo mensagem de sucesso "Atualização realizada com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"
