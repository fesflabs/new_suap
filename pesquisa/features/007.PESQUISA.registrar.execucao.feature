# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Registro da Execução do Projeto de Pesquisa

      @do_document
      Cenário: Registro da Execução das Atividades
      Ação executada pelo Servidor (coordenador do projeto).
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108003" e senha "abcd"
             E a data do sistema for "20/01/2018"
             E acesso o menu "Pesquisa::Projetos::Meus Projetos"
         Então vejo a página "Meus Projetos"
        Quando clico no ícone de exibição
         Então vejo a página "Projeto de Pesquisa"
         Quando clico na aba "Objetivos Específicos"
         E olho a linha "Descrição da Atividade 1"
         Então vejo o botão "Registrar Execução"
         Quando clico no botão "Registrar Execução"
            E olho para o popup
            Então vejo os seguintes campos no formulário
               | Campo                                                      | Tipo     |
               | Indicadores Qualitativos                                   | Lista    |
               | Início da Execução                                         | Data    |
               | Fim da Execução                                            | Data    |
               | Descrição da Atividade Realizada                           | TextArea |
               | Arquivo                                                    | arquivo    |


             E vejo o botão "Salvar"


        Quando preencho o formulário com os dados
               | Campo                                                      | Tipo     | Valor                    |
               | Indicadores Qualitativos                                   | Lista    | Atendido                 |
               | Início da Execução                                         | Data    | 01/04/2018               |
               | Fim da Execução                                            | Data    | 30/04/2018               |

             E clico no botão "Salvar"

         Então vejo mensagem de sucesso "Execução registrada com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"

      @do_document
      Cenário: Cadastro das Fotos
      Cadastro das fotos que ilustram as atividades executadas no projeto.
      Ação executada pelo Servidor (coordenador do projeto).
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108003" e senha "abcd"
             E a data do sistema for "20/01/2018"
             E acesso o menu "Pesquisa::Projetos::Meus Projetos"
         Então vejo a página "Meus Projetos"
        Quando clico no ícone de exibição
         Então vejo a página "Projeto de Pesquisa"
         Quando clico na aba "Fotos"
         Então vejo o botão "Adicionar Foto"
         Quando clico no botão "Adicionar Foto"
            Então vejo os seguintes campos no formulário
               | Campo                                                 | Tipo     |
               | Legenda                                               | TextArea |
               | Fotos                                                | Arquivo  |
             E vejo o botão "Enviar"

        Quando preencho o formulário com os dados
               | Campo                                                      | Tipo     | Valor               |
               | Legenda                                                    | TextArea | Legenda da foto     |
               | Fotos                                                     | Arquivo  | foto_projeto.png    |

             E clico no botão "Enviar"

         Então vejo mensagem de sucesso "Foto adicionada com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"


      @do_document
      Cenário: Registro dos Gastos
      Para cada desembolso (gasto previsto durante a fase do planejamento), o coordenador deve registrar que o gasto efetivamente ocorreu.
      Caso não tenha ocorrido, o coordenador do projeto registra o gasto com o valor R$ 0,00 e descreve no campo 'Observação' o motivo pelo qual não
      houve necessidade do gasto ou o motivo que impediu a sua realização.
      Ação executada pelo Servidor (coordenador do projeto).
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108003" e senha "abcd"
             E a data do sistema for "20/01/2018"
             E acesso o menu "Pesquisa::Projetos::Meus Projetos"
         Então vejo a página "Meus Projetos"
        Quando clico no ícone de exibição
         Então vejo a página "Projeto de Pesquisa"
         Quando clico na aba "Plano de Desembolso"
         E olho a linha "339018 - Auxílio Financeiro a Estudantes - Pagamento das bolsas de dois alunos, no valor de R$ 500,00 cada"
         Então vejo o botão "Gerenciar Gasto"
         Quando clico no botão "Gerenciar Gasto"
            Então vejo a página "Gastos Registrados"
            E vejo os seguintes campos no formulário
               | Campo                                                      | Tipo     |
               | Ano                                                        | Lista    |
               | Mês                                                        | Lista    |
               | Descrição                                                  | TextArea |
               | Quantidade                                                 | Texto    |
               | Valor Unitário (R$)                                        | Texto    |
               | Observação                                                 | TextArea |
               | Nota Fiscal ou Cupom                                       | Arquivo    |
               | Cotação de Preços                                          | Arquivo    |


             E vejo o botão "Salvar"
         Quando preencho o formulário com os dados
               | Campo                                                      | Tipo     | Valor                           |
               | Ano                                                        | Lista    | 2018                            |
               | Mês                                                        | Lista    | 5                               |
               | Descrição                                                  | TextArea | Obs sobre o registro do gasto   |
               | Quantidade                                                 | Texto    | 1                               |
               | Valor Unitário (R$)                                        | Texto    | 200,00                          |

             E clico no botão "Salvar"

         Então vejo mensagem de sucesso "Gasto registrado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"

       @do_document
      Cenário: Cadastro de Anexo do Projeto
      Cadastro de documento diverso relacionado ao projeto.
      Ação executada pelo Servidor (coordenador do projeto).
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108003" e senha "abcd"
             E a data do sistema for "20/01/2018"
             E acesso o menu "Pesquisa::Projetos::Meus Projetos"
         Então vejo a página "Meus Projetos"
          Quando clico no ícone de exibição
         Então vejo a página "Projeto de Pesquisa"
         Quando clico na aba "Anexos"
         Então vejo o botão "Adicionar Anexo"
         Quando clico no botão "Adicionar Anexo"
            Então vejo os seguintes campos no formulário
               | Campo                                                 | Tipo     |
               | Descrição                                             | Texto |
               | Membro da Equipe                                      | Lista |
               | Arquivo                                                | Arquivo  |
             E vejo o botão "Salvar"

        Quando preencho o formulário com os dados
               | Campo                                                      | Tipo     | Valor               |
               | Descrição                                                  | Texto    | Folha de Frequência do aluno     |
               | Membro da Equipe                                           | Lista    | 20191101011081 |
               | Arquivo                                                     | Arquivo  | Arquivo.pdf    |

             E clico no botão "Salvar"

         Então vejo mensagem de sucesso "Anexo cadastrado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"

      @do_document
      Cenário: Cadastro de Relatório Parcial
      Durante a execução do projeto, os relatórios parciais podem ser cadastrados.
      Ação executada pelo Servidor (coordenador do projeto).
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108003" e senha "abcd"
             E a data do sistema for "20/01/2018"
             E acesso o menu "Pesquisa::Projetos::Meus Projetos"
         Então vejo a página "Meus Projetos"
        Quando clico no ícone de exibição
         Então vejo a página "Projeto de Pesquisa"
         Quando clico na aba "Relatórios"
         Então vejo o botão "Adicionar Relatório"
         Quando clico no botão "Adicionar Relatório"
         Então vejo a página "Adicionar Relatório"
            E vejo os seguintes campos no formulário
               | Campo                                                      | Tipo     |
               | Descrição                                                  | Texto    |
               | Tipo do Relatório                                          | Lista    |
               | Arquivo                                                    | Arquivo |
               | Observação                                                 | TextArea |


             E vejo o botão "Salvar"
         Quando preencho o formulário com os dados
               | Campo                                                      | Tipo     | Valor                           |
                | Descrição                                                  | Texto   | Relatório parcial do projeto    |
               | Tipo do Relatório                                          | Lista    | Parcial |
               | Arquivo                                                    | Arquivo  | relatorio_parcial.pdf |
               | Observação                                                 | TextArea | Exemplo de cadastro do relatório parcial |

             E clico no botão "Salvar"

         Então vejo mensagem de sucesso "Relatório adicionado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"

       @do_document
      Cenário: Registro da Frequência Diária
      Os membros do projeto registram suas atividades diárias.

          Dado acesso a página "/"
        Quando realizo o login com o usuário "20191101011081" e senha "abcd"
         E a data do sistema for "20/01/2018"
         E clico no link "Título do projeto"
         Então vejo a página "Projeto de Pesquisa"
         Quando clico na aba "Registros de Frequência/Atividade"
         Então vejo o botão "Cadastrar Frequência/Atividade"
         Quando clico no botão "Cadastrar Frequência/Atividade"
            Então vejo a página "Registrar Frequência/Atividade"
            E vejo os seguintes campos no formulário
               | Campo                                                      | Tipo     |
               | Descrição                                                   | TextArea |
               | Data                                                        | Data     |
             E vejo o botão "Salvar"
         Quando preencho o formulário com os dados
               | Campo                                                     | Tipo     | Valor                           |
               | Descrição                                                 | TextArea    | Descrição da atividade do dia    |
               | Data                                                      | Data     | 20/02/2018                               |
             E clico no botão "Salvar"

         Então vejo mensagem de sucesso "Frequência/Atividade cadastrada com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"
