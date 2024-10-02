# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro e Configuração do Edital de Publicação de Obras

      Cenário: Adicionando os usuários necessários para os testes da editora
          Dado os dados básicos para a editora
            E  os seguintes usuários
                | Nome                  | Matrícula | Setor    | Lotação  | Email                     | CPF            | Senha | Grupo                     |
                | Integrante  Editora   | 108007    | CZN      | CZN      | int_editora@ifrn.edu.br   | 645.433.195-40 | abcd  | Integrante da Editora     |
                | Conselheiro Editora   | 108008    | DIAC/CZN | DIAC/CZN | conselheiro@ifrn.edu.br   | 188.135.291-98 | abcd  | Conselheiro Editorial     |
                | Revisor Editora       | 108009    | DIAC/CZN | DIAC/CZN | revisor@ifrn.edu.br       | 921.728.444-03 | abcd  | Revisor de Obra           |
                | Diagramador Editora   | 108010    | DIAC/CZN | DIAC/CZN | diagramador@ifrn.edu.br   | 458.658.545-50 | abcd  | Diagramador de Obra       |
                | Bibliotecário Editora | 108011    | DIAC/CZN | DIAC/CZN | bibliotecario@ifrn.edu.br | 830.665.156-13 | abcd  | Bibliotecário da Pesquisa |
                | Autor Obra            | 108012    | DIAC/CZN | DIAC/CZN | servidor_a@ifrn.edu.br    | 232.607.644-37 | abcd  | Servidor                  |


   Esquema do Cenário: Verifica a visibilidade do menu Pesquisa e da adição do Edital de Publicação de Obras pelo <Papel>
        Dado acesso a página "/"
        Quando realizo o login com o usuário "<Papel>" e senha "abcd"
        Então vejo o item de menu "Pesquisa::Editora::Submissão de Obras::Editais"
        Quando acesso a página "/admin/pesquisa/editalsubmissaoobra/"
        Então vejo a página "Editais para Submissão de Obra"
        E vejo o botão "Adicionar Edital para Submissão de Obra"
        Quando acesso o menu "Sair"
          Exemplos:
              | Papel  |
              | 108007 |

      @do_document
      Cenário: Cadastro do Edital
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108007" e senha "abcd"
             E acesso o menu "Pesquisa::Editora::Submissão de Obras::Editais"
         Então vejo a página "Editais para Submissão de Obra"
             E vejo o botão "Adicionar Edital para Submissão de Obra"
        Quando clico no botão "Adicionar Edital para Submissão de Obra"
         Então vejo a página "Adicionar Edital para Submissão de Obra"
             E vejo os seguintes campos no formulário
               | Campo                                         | Tipo     |
               | Título                                        | Texto    |
               | Linhas Editoriais                             | FilteredSelectMultiple |
               | Arquivo do Edital                             | Arquivo  |
               | Data de Início da Submissão                   | Data     |
               | Data de Término da Submissão                  | Data     |
               | Data de Início da Verificação de Plágio       | Data     |
               | Data de Término da Verificação de Plágio      | Data     |
               | Data de Início de Análise de Especialista     | Data     |
               | Data de Término de Análise de Especialista    | Data     |
               | Data de Início de Validação do Conselho       | Data     |
               | Data de Término de Validação do Conselho      | Data     |
               | Data de Início de Aceite                      | Data     |
               | Data de Término de Aceite                     | Data     |
               | Data de Início de Envio dos Termos            | Data     |
               | Data de Término de Envio dos Termos           | Data     |
               | Data de Início de Revisão Linguística/Textual | Data     |
               | Data de Término de Revisão Linguística/Textual| Data     |
               | Data de Início de Diagramação                 | Data     |
               | Data de Término de Diagramação                | Data     |
               | Data de Início de Solicitação ISBN            | Data     |
               | Data de Término de Solicitação ISBN           | Data     |
               | Data de Início de Impressão de Boneco         | Data     |
               | Data de Término de Impressão de Boneco        | Data     |
               | Data de Revisão de Layout                     | Data     |
               | Data de Início de Correção Final              | Data     |
               | Data de Término de Correção Final             | Data     |
               | Data de Início de Análise de Liberação        | Data     |
               | Data de Término de Análise de Liberação       | Data     |
               | Data de Início de Impressão                   | Data     |
               | Data de Término de Impressão                  | Data     |
               | Data de Lançamento                            | Data     |
               | Local de Lançamento                           | Texto    |
               | Observações do Lançamento                     | Texto    |
               | Instruções para Submissão de Obra             | TextArea |
               | Manual do Autor                               | Arquivo  |
               | Ficha de Avaliação para Parecerista           | Arquivo    |

             E vejo o botão "Salvar"

        Quando preencho o formulário com os dados
               | Campo                                         | Tipo                   | Valor                         |
               | Título                                        | Texto                  | Edital para publicação        |
               | Linhas Editoriais                             | FilteredSelectMultiple | Linha Editorial 01            |
               | Arquivo do Edital                             | Arquivo                | publicacao_edital.png         |
               | Data de Início da Submissão                   | Data                   | 01/01/2018                    |
               | Data de Término da Submissão                  | Data                   | 10/01/2018                    |
               | Data de Início da Verificação de Plágio       | Data                   | 11/01/2018                    |
               | Data de Término da Verificação de Plágio      | Data                   | 15/01/2018                    |
               | Data de Início de Análise de Especialista     | Data                   | 16/01/2018                    |
               | Data de Término de Análise de Especialista    | Data                   | 28/01/2018                    |
               | Data de Início de Aceite                      | Data                   | 25/01/2018                    |
               | Data de Término de Aceite                     | Data                   | 28/01/2018                    |
               | Data de Início de Validação do Conselho       | Data                   | 21/01/2018                    |
               | Data de Término de Validação do Conselho      | Data                   | 28/01/2018                    |
               | Data de Início de Envio dos Termos            | Data                   | 29/01/2018                    |
               | Data de Término de Envio dos Termos           | Data                   | 31/01/2018                    |
               | Data de Início de Revisão Linguística/Textual | Data                   | 01/02/2018                    |
               | Data de Término de Revisão Linguística/Textual| Data                   | 04/02/2018                    |
               | Data de Início de Diagramação                 | Data                   | 05/02/2018                    |
               | Data de Término de Diagramação                | Data                   | 08/02/2018                    |
               | Data de Início de Solicitação ISBN            | Data                   | 09/02/2018                    |
               | Data de Término de Solicitação ISBN           | Data                   | 13/02/2018                    |
               | Data de Início de Impressão de Boneco         | Data                   | 10/02/2018                    |
               | Data de Término de Impressão de Boneco        | Data                   | 18/02/2018                    |
               | Data de Revisão de Layout                     | Data                   | 19/02/2018                    |
               | Data de Início de Correção Final              | Data                   | 10/02/2018                    |
               | Data de Término de Correção Final             | Data                   | 23/02/2018                    |
               | Data de Início de Análise de Liberação        | Data                   | 10/02/2018                    |
               | Data de Término de Análise de Liberação       | Data                   | 01/03/2018                    |
               | Data de Início de Impressão                   | Data                   | 10/02/2018                    |
               | Data de Término de Impressão                  | Data                   | 05/03/2018                    |
               | Data de Lançamento                            | Data                   | 01/04/2018                    |
               | Local de Lançamento                           | Texto                  | Local do lançamento das obras |
               | Observações do Lançamento                     | Texto                  | Observações sobre o lançamento|
               | Instruções para Submissão de Obra             | Texto Rico             | Instruções                    |
               | Manual do Autor                               | Arquivo                | manual.png                    |
               | Ficha de Avaliação para Parecerista           | Arquivo                | ficha_avaliacao.png           |


             E clico no botão "Salvar"

         Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"