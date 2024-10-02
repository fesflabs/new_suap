# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Submissão de Projeto de Pesquisa

      @do_document
      Cenário: Cadastro do Projeto
      Formulário de submissão com as informações básicas do projeto. Após o envio dos dados, o projeto estará cadastrado mas ainda não terá sido submetido,
      ou seja, a situação do projeto será 'em edição' (rascunho). Só após o cadastro das demais informações obrigatórias, descritas nos próximos passos, é que o projeto poderá ser efetivamente submetido.
      Ação executada pelo Servidor (coordenador do projeto).
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108003" e senha "abcd"
            E a data do sistema for "08/01/2018"
            E acesso o menu "Pesquisa::Projetos::Submeter Projetos"
         Então vejo a página "Editais de Pesquisa e de Inovação com Inscrições Abertas"
             E vejo o botão "Adicionar Projeto"
        Quando clico no botão "Adicionar Projeto"
         Então vejo a página "Adicionar Projeto"
             E vejo os seguintes campos no formulário
               | Campo                                                      | Tipo         |
               | Campus                                                     | Autocomplete |
               | Título do projeto                                          | Texto        |
               | Início da Execução                                         | Data        |
               | Término da Execução                                        | Texto        |
               | Área do Conhecimento                                       | Lista        |
               | Grupo de Pesquisa                                          | Lista        |
               | Palavras-Chaves                                            | Texto        |
               | Resumo                                                     | Textarea     |
               | Introdução                                                 | Textarea     |
               | Justificativa                                              | Textarea     |
               | Fundamentação Teórica                                      | Textarea     |
               | Objetivo Geral                                             | Textarea     |
               | Metodologia da execução do projeto                         | Textarea     |
               | Acompanhamento e avaliação do projeto durante a execução   | Textarea     |
               | Resultados Esperados                                       | Textarea     |
               | Referências Bibliográficas                                 | Textarea     |
             E vejo o botão "Salvar"

        Quando preencho o formulário com os dados
            | Campo                                                    | Tipo         | Valor                                   |
            | Campus                                                   | Autocomplete | CZN                                     |
            | Título do projeto                                        | Texto        | Título do projeto                       |
            | Início da Execução                                       | Data        | 01/03/2018                              |
            | Término da Execução                                      | Data        | 12/12/2018                              |
            | Área do Conhecimento                                     | Lista        | MATEMÁTICA (CIÊNCIAS EXATAS E DA TERRA) |
            | Grupo de Pesquisa                                        | Lista        | Grupo de Pesquisa                       |
            | Palavras-Chaves                                          | Texto        | teste da palavra;                       |
            | Resumo                                                   | Texto Rico   | Texto do Resumo                         |
            | Introdução                                               | Texto Rico   | Texto da Introdução                     |
            | Justificativa                                            | Texto Rico   | Texto da Justificativa                  |
            | Fundamentação Teórica                                    | Texto Rico   | Texto da Fundamentação Teórica          |
            | Objetivo Geral                                           | Texto Rico   | Texto do objetivo Geral                 |
            | Metodologia da execução do projeto                       | Texto Rico   | Texto da metodologia                    |
            | Acompanhamento e avaliação do projeto durante a execução | Texto Rico   | Texto do acompanhamento                 |
            | Resultados Esperados                                     | Texto Rico   | Texto dos resultados                    |
            | Referências Bibliográficas                               | Texto Rico   | Texto das referências                   |
             E clico no botão "Salvar"

        Então vejo mensagem de sucesso "Projeto cadastrado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"

      @do_document
      Cenário: Inclusão de Servidor na Equipe
      Cadastro do servidor membro do projeto de pesquisa.
      Ação executada pelo Servidor (coordenador do projeto).
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108003" e senha "abcd"
             E acesso o menu "Pesquisa::Projetos::Meus Projetos"
         Então vejo a página "Meus Projetos"
        Quando clico no ícone de exibição
         Então vejo a página "Projeto de Pesquisa"
         Quando clico na aba "Equipe"
         Então vejo o botão "Adicionar Servidor"
         Quando clico no botão "Adicionar Servidor"
             E olho para o popup
             Então vejo os seguintes campos no formulário
               | Campo                                                      | Tipo            |
               | Vínculo                                                    | Lista           |
               | Carga Horária                                              | Texto           |
               | Participante                                               | Autocomplete    |
               | Data de Entrada                                               | Data     |


             E vejo o botão "Salvar"


        Quando preencho o formulário com os dados
               | Campo                                                      | Tipo            | Valor                    |
               | Vínculo                                                    | Lista           | Bolsista                 |
               | Carga Horária                                              | Texto           | 6                        |
               | Participante                                               | Autocomplete    | Servidor Projeto            |
               | Data de Entrada                                               | Data     |   01/03/2018 |


             E clico no botão "Salvar"
         Então vejo mensagem de sucesso "Participante adicionado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"

      @do_document
      Cenário: Inclusão de Aluno na Equipe
      Cadastro do aluno membro do projeto de pesquisa.
      Ação executada pelo Servidor (coordenador do projeto).
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108003" e senha "abcd"
             E acesso o menu "Pesquisa::Projetos::Meus Projetos"
         Então vejo a página "Meus Projetos"
        Quando clico no ícone de exibição
         Então vejo a página "Projeto de Pesquisa"
         Quando clico na aba "Equipe"
         Então vejo o botão "Adicionar Aluno"
         Quando clico no botão "Adicionar Aluno"
             E olho para o popup
             Então vejo os seguintes campos no formulário
               | Campo                                                      | Tipo            |
               | Vínculo                                                    | Lista           |
               | Carga Horária                                              | Texto           |
               | Participante                                               | Autocomplete    |
               | Data de Entrada                                               | Data     |


             E vejo o botão "Salvar"


        Quando preencho o formulário com os dados
               | Campo                                                      | Tipo            | Valor                    |
               | Vínculo                                                    | Lista           | Bolsista                 |
               | Carga Horária                                              | Texto           | 6                        |
               | Participante                                               | Autocomplete    | Aluno do Projeto         |
               | Data de Entrada                                               | Data     |   01/03/2018 |


             E clico no botão "Salvar"
         Então vejo mensagem de sucesso "Participante adicionado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"


      @do_document
      Cenário: Cadastro das Metas
      Cadastro das metas do projeto.
      Ação executada pelo Servidor (coordenador do projeto).
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108003" e senha "abcd"
             E acesso o menu "Pesquisa::Projetos::Meus Projetos"
         Então vejo a página "Meus Projetos"
        Quando clico no ícone de exibição
         Então vejo a página "Projeto de Pesquisa"
         Quando clico na aba "Objetivos Específicos"
             Então vejo o botão "Adicionar Meta"
         Quando clico no botão "Adicionar Meta"
             E olho para o popup
             Então vejo os seguintes campos no formulário
               | Campo                                                      | Tipo     |
               | Ordem                                                      | Texto    |
               | Descrição                                                  | TextArea |


             E vejo o botão "Salvar"

        Quando preencho o formulário com os dados
               | Campo                                                      | Tipo     | Valor                                       |
               | Ordem                                                      | Texto    | 1                                           |
               | Descrição                                                  | TextArea | Descrição da Meta 1                         |

             E clico no botão "Salvar"

         Então vejo mensagem de sucesso "Meta adicionada com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"

      @do_document
      Cenário: Cadastro das Atividades
      Cadastro das atividades que serão realizadas dentro de cada meta do projeto.
      Ação executada pelo Servidor (coordenador do projeto).
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108003" e senha "abcd"
             E acesso o menu "Pesquisa::Projetos::Meus Projetos"
         Então vejo a página "Meus Projetos"
        Quando clico no ícone de exibição
         Então vejo a página "Projeto de Pesquisa"
         Quando clico na aba "Objetivos Específicos"
         Então vejo o botão "Adicionar Atividade"
         Quando clico no botão "Adicionar Atividade"
             E olho para o popup
             Então vejo os seguintes campos no formulário
               | Campo                                                      | Tipo     |
               | Ordem                                                      | Texto    |
               | Descrição                                                  | TextArea |


               | Resultados Esperados                                       | TextArea |
               | Responsável                                                | Lista    |
               | Início da Execução                                         | Data    |
               | Fim da Execução                                            | Data    |


             E vejo o botão "Salvar"

        Quando preencho o formulário com os dados
               | Campo                                                      | Tipo     | Valor                    |
               | Ordem                                                      | Texto    | 1                        |
               | Descrição                                                  | TextArea | Descrição da Atividade 1 |


               | Resultados Esperados                                       | TextArea | Verificação de qualidade |
               | Responsável                                                | Lista    | Servidor Projeto         |
               | Início da Execução                                         | Data    | 01/04/2018               |
               | Fim da Execução                                            | Data    | 30/04/2018               |

             E clico no botão "Salvar"

         Então vejo mensagem de sucesso "Etapa adicionada com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"

      @do_document
      Cenário: Cadastro das Memórias de Cálculo
      A memória de cálculo serve para descrever em detalhes os gastos que serão realizados no projeto. Nesta aba do projeto existe o Demonstrativo do Plano de Aplicação/Memória de Cálculo e Desembolso,
      onde, na coluna 'Valor Reservado' consta o valor total disponível para o projeto na rubrica em específico, conforme cadastrado na fonte de recurso do edital. Na seção 'Planejado', a coluna 'Valor Planejado' exibe a soma de todas as memórias de cálculo cadastradas pelo coordenador do projeto.
      Já na coluna 'Valor Distribuído' consta a soma de todos os desembolsos que foram cadastrados pelo coordenador e na coluna 'Valor Disponível' consta a diferença entre a soma das memórias de cálculo e a soma dos desembolsos.
      Na seção 'Execução', a coluna 'Valor Executado' é a soma de todos os registros de gastos cadastrados pelo coordenador do projeto e a coluna 'Valor Disponível' é a diferença entre o total de desembolsos e o total de gastos.
      Ação executada pelo Servidor (coordenador do projeto).
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108003" e senha "abcd"
             E acesso o menu "Pesquisa::Projetos::Meus Projetos"
         Então vejo a página "Meus Projetos"
        Quando clico no ícone de exibição
         Então vejo a página "Projeto de Pesquisa"
         Quando clico na aba "Plano de Aplicação"
         Então vejo o botão "Adicionar Memória de Cálculo"
         Quando clico no botão "Adicionar Memória de Cálculo"
             E olho para o popup
             Então vejo os seguintes campos no formulário
               | Campo                                                      | Tipo     |
               | Despesa                                                    | Autocomplete    |
               | Descrição                                                  | TextArea |
               | Unidade de Medida                                          | Texto    |
               | Quantidade                                                 | Texto    |
               | Valor Unitário (R$)                                        | Texto    |


             E vejo o botão "Salvar"


        Quando preencho o formulário com os dados
               | Campo                                                      | Tipo     | Valor                                             |
               | Despesa                                                    | Autocomplete    | Auxílio Financeiro a Estudantes            |
               | Descrição                                                  | TextArea | Pagamento das bolsas de dois alunos, no valor de R$ 500,00 cada                     |
               | Unidade de Medida                                          | Texto    | Unidade                                           |
               | Quantidade                                                 | Texto    | 1                                                 |
               | Valor Unitário (R$)                                        | Texto    | 10.000,00                                          |

             E clico no botão "Salvar"

         Então vejo mensagem de sucesso "Item adicionado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"

      @do_document
      Cenário: Cadastro dos Desembolsos
      Com base na memória de cálculo, neste passo o coordenador do projeto informa quando pretende realizar os gastos(desembolsos) dos recursos.
      Por exemplo, uma memória de cálculo no valor de R$ 10.000,00 prevista para pagamento de alunos bolsistas pode ter 10 desembolsos, no valor de R$1.000,00 cada,
      que serão executados ao longo de 10 meses.
      Ação executada pelo Servidor (coordenador do projeto).
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108003" e senha "abcd"
             E acesso o menu "Pesquisa::Projetos::Meus Projetos"
         Então vejo a página "Meus Projetos"
        Quando clico no ícone de exibição
         Então vejo a página "Projeto de Pesquisa"
         Quando clico na aba "Plano de Desembolso"
         Então vejo o botão "Adicionar Item"
         Quando clico no botão "Adicionar Item"
             E olho para o popup
             Então vejo os seguintes campos no formulário
               | Campo                                                      | Tipo     |
               | Mémoria de Cálculo                                         | Lista    |
               | Ano                                                        | Autocomplete    |
               | Mês                                                        | Lista    |
               | Valor (R$)                                                 | Texto    |
               | Repetir Desembolso até o mês                               | Texto    |



             E vejo o botão "Salvar"


        Quando preencho o formulário com os dados
               | Campo                                                      | Tipo     | Valor                                                                             |
               | Mémoria de Cálculo                                         | Lista    | 339018 - Auxílio Financeiro a Estudantes - Pagamento das bolsas de dois alunos, no valor de R$ 500,00 cada          |
               | Ano                                                        | Autocomplete    | 2018                                                                              |
               | Mês                                                        | Lista    | 1                                                                                 |
               | Valor (R$)                                                 | Texto    | 1.000,00                                                                            |

             E clico no botão "Salvar"

         Então vejo mensagem de sucesso "Desembolso adicionado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"

      @do_document
      Cenário: Submissão do Projeto
      Após o cadastro de todas as informações obrigatórias, o coordenador do projeto está apto a realizar a submissão do projeto.
      Ação executada pelo Servidor (coordenador do projeto).
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108003" e senha "abcd"
             E acesso o menu "Pesquisa::Projetos::Meus Projetos"
         Então vejo a página "Meus Projetos"
        Quando clico no ícone de exibição
         Então vejo a página "Projeto de Pesquisa"
             E vejo o botão "Enviar Projeto"
         Quando clico no botão "Enviar Projeto"
         Então vejo mensagem de sucesso "Projeto enviado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"


