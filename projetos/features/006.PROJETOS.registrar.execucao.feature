      # -*- coding: utf-8 -*-
      # language: pt

      Funcionalidade: Registro da Execução do Projeto de Extensão

      @do_document
      Cenário: Cadastro dos Beneficiários Atendidos
      Durante a execução do projeto, o coordenador irá registrar a quantidade de pessoas e de instituições que foram efetivamente beneficiadas pelo projeto.
      Ação executada pelo Servidor (coordenador do projeto).
      Dado acesso a página "/"
      Quando realizo o login com o usuário "110003" e senha "abcd"
      E a data do sistema for "20/01/2018"
      E acesso o menu "Extensão::Projetos::Meus Projetos"
      Então vejo a página "Meus Projetos"
      E vejo o botão "Visualizar"
      Quando clico no botão "Visualizar"
      Então vejo a página "Projeto de Extensão"
      Quando clico na aba "Caracterização dos Beneficiários"
      E olho a linha "Movimentos Sociais"
      Então vejo o botão "Registrar"
      Quando clico no botão "Registrar"
      E olho para o popup
      Então vejo os seguintes campos no formulário
      | Campo                                     | Tipo     |
      | Quantidade Atendida                       | Texto    |
      | Descreva os Beneficiários do Público-Alvo | TextArea |

      E vejo o botão "Salvar"

      Quando preencho o formulário com os dados
      | Campo                                     | Tipo     | Valor                            |
      | Quantidade Atendida                       | Texto    | 12                               |
      | Descreva os Beneficiários do Público-Alvo | TextArea | descricao sobre os beneficiários |

      E clico no botão "Salvar"

      Então vejo mensagem de sucesso "Caracterização registrada com sucesso."

      Cenário: Sai do sistema
      Quando acesso o menu "Sair"


      @do_document
      Cenário: Registro da Execução das Atividades
      Dado acesso a página "/"
      Quando realizo o login com o usuário "110003" e senha "abcd"
      E a data do sistema for "20/01/2018"
      E acesso o menu "Extensão::Projetos::Meus Projetos"
      Então vejo a página "Meus Projetos"
      E vejo o botão "Visualizar"
      Quando clico no botão "Visualizar"
      Então vejo a página "Projeto de Extensão"
      Quando clico na aba "Metas/Atividades"
      E olho a linha "Descrição da Atividade 1"
      Então vejo o botão "Registrar Execução"
      Quando clico no botão "Registrar Execução"
      E olho para o popup
      Então vejo os seguintes campos no formulário
      | Campo                            | Tipo     |
      | Indicadores Qualitativos         | Lista    |
      | Quantidade                       | Texto    |
      | Início da Execução               | Data     |
      | Fim da Execução                  | Data     |
      | Descrição da Atividade Realizada | TextArea |
      | Arquivo                          | arquivo  |


      E vejo o botão "Salvar"

      Quando preencho o formulário com os dados
      | Campo                    | Tipo  | Valor      |
      | Indicadores Qualitativos | Lista | Atendido   |
      | Quantidade               | Texto | 1          |
      | Início da Execução       | Data  | 01/04/2018 |
      | Fim da Execução          | Data  | 30/04/2018 |

      E clico no botão "Salvar"

      Então vejo mensagem de sucesso "Execução registrada com sucesso."

      Cenário: Sai do sistema
      Quando acesso o menu "Sair"


      @do_document
      Cenário: Cadastro de Anexo do Projeto
      Cadastro de documento diverso relacionado ao projeto.
      Ação executada pelo Servidor (coordenador do projeto).
      Dado acesso a página "/"
      Quando realizo o login com o usuário "110003" e senha "abcd"
      E a data do sistema for "20/01/2018"
      E acesso o menu "Extensão::Projetos::Meus Projetos"
      Então vejo a página "Meus Projetos"
      E vejo o botão "Visualizar"
      Quando clico no botão "Visualizar"
      Então vejo a página "Projeto de Extensão"
      Quando clico na aba "Anexos"
      Então vejo o botão "Adicionar Anexo"
      Quando clico no botão "Adicionar Anexo"
      Então vejo os seguintes campos no formulário
      | Campo            | Tipo    |
      | Descrição        | Texto   |
      | Membro da Equipe | Lista   |
      | Arquivo          | Arquivo |
      E vejo o botão "Salvar"

      Quando preencho o formulário com os dados
      | Campo            | Tipo    | Valor                        |
      | Descrição        | Texto   | Folha de Frequência do aluno |
      | Membro da Equipe | Lista   | 20191101011101               |
      | Arquivo          | Arquivo | Arquivo.pdf                  |

      E clico no botão "Salvar"

      Então vejo mensagem de sucesso "Anexo cadastrado com sucesso."

      Cenário: Sai do sistema
      Quando acesso o menu "Sair"


      @do_document
      Cenário: Cadastro das Fotos
      Cadastro das fotos que ilustram as atividades executadas no projeto.
      Ação executada pelo Servidor (coordenador do projeto).
      Dado acesso a página "/"
      Quando realizo o login com o usuário "110003" e senha "abcd"
      E a data do sistema for "20/01/2018"
      E acesso o menu "Extensão::Projetos::Meus Projetos"
      Então vejo a página "Meus Projetos"
      E vejo o botão "Visualizar"
      Quando clico no botão "Visualizar"
      Então vejo a página "Projeto de Extensão"
      Quando clico na aba "Fotos"
      Então vejo o botão "Adicionar Foto"
      Quando clico no botão "Adicionar Foto"
      Então vejo os seguintes campos no formulário
      | Campo   | Tipo     |
      | Legenda | TextArea |
      | Imagem  | Arquivo  |
      E vejo o botão "Salvar"

      Quando preencho o formulário com os dados
      | Campo   | Tipo     | Valor            |
      | Legenda | TextArea | Legenda da foto  |
      | Imagem  | Arquivo  | foto_projeto.png |

      E clico no botão "Salvar"

      Então vejo mensagem de sucesso "Foto adicionada com sucesso."

      Cenário: Sai do sistema
      Quando acesso o menu "Sair"

      @do_document
      Cenário: Cadastro das Prestações de Contas
      Cadastro dos comprovantes para prestação de contas das atividades executadas no projeto.
      Ação executada pelo Servidor (coordenador do projeto).
      Dado acesso a página "/"
      Quando realizo o login com o usuário "110003" e senha "abcd"
      E a data do sistema for "20/01/2018"
      E acesso o menu "Extensão::Projetos::Meus Projetos"
      Então vejo a página "Meus Projetos"
      E vejo o botão "Visualizar"
      Quando clico no botão "Visualizar"
      Então vejo a página "Projeto de Extensão"
      Quando clico na aba "Prestação de Contas"
      Então vejo o botão "Adicionar Extrato Mensal"
      Quando clico no botão "Adicionar Extrato Mensal"
      Então vejo os seguintes campos no formulário
      | Campo   | Tipo         |
      | Ano     | Autocomplete |
      | Mês     | Lista        |
      | Arquivo | Arquivo      |
      E vejo o botão "Salvar"

      Quando preencho o formulário com os dados
      | Campo   | Tipo         | Valor           |
      | Ano     | Autocomplete | 2018            |
      | Mês     | Lista        | Janeiro         |
      | Arquivo | Arquivo      | comprovante.pdf |

      E clico no botão "Salvar"

      Então vejo mensagem de sucesso "Extrato cadastrado com sucesso."

      Quando clico na aba "Prestação de Contas"
      Então vejo o botão "Adicionar Comprovante de GRU"
      Quando clico no botão "Adicionar Comprovante de GRU"
      Então vejo os seguintes campos no formulário
      | Campo                           | Tipo    |
      | Descrição                       | Texto   |
      | Comprovante de Pagamento da GRU | Arquivo |
      E vejo o botão "Salvar"

      Quando preencho o formulário com os dados
      | Campo                           | Tipo    | Valor                             |
      | Descrição                       | Texto   | Devolução das sobras dos recursos |
      | Comprovante de Pagamento da GRU | Arquivo | comprovante.pdf                   |

      E clico no botão "Salvar"

      Então vejo mensagem de sucesso "Comprovante cadastrado com sucesso."

      Cenário: Sai do sistema
      Quando acesso o menu "Sair"


      @do_document
      Cenário: Registro dos Gastos
      Para cada desembolso (gasto previsto durante a fase do planejamento), o coordenador deve registrar que o gasto efetivamente ocorreu.
      Caso não tenha ocorrido, o coordenador do projeto registra o gasto com o valor R$ 0,00 e descreve no campo 'Observação' o motivo pelo qual não
      houve necessidade do gasto ou o motivo que impediu a sua realização.
      Ação executada pelo Servidor (coordenador do projeto).
      Dado acesso a página "/"
      Quando realizo o login com o usuário "110003" e senha "abcd"
      E a data do sistema for "20/01/2018"
      E acesso o menu "Extensão::Projetos::Meus Projetos"
      Então vejo a página "Meus Projetos"
      E vejo o botão "Visualizar"
      Quando clico no botão "Visualizar"
      Então vejo a página "Projeto de Extensão"
      Quando clico na aba "Plano de Desembolso"
      E olho a linha "339018 - Auxílio Financeiro a Estudantes / PROEX - Pagamento das bolsas de dois alunos, no valor de R$ 500,00 cada"
      Então vejo o botão "Gerenciar Gasto"
      Quando clico no botão "Gerenciar Gasto"
      Então vejo a página "Gastos Registrados"
      E vejo os seguintes campos no formulário
      | Campo                | Tipo     |
      | Ano                  | Lista    |
      | Mês                  | Lista    |
      | Descrição            | TextArea |
      | Quantidade           | Texto    |
      | Valor Unitário (R$)  | Texto    |
      | Observação           | TextArea |
      | Nota Fiscal ou Cupom | Arquivo  |
      | Cotação de Preços    | Arquivo  |


      E vejo o botão "Salvar"
      Quando preencho o formulário com os dados
      | Campo               | Tipo     | Valor                         |
      | Ano                 | Lista    | 2018                          |
      | Mês                 | Lista    | 5                             |
      | Descrição           | TextArea | Obs sobre o registro do gasto |
      | Quantidade          | Texto    | 1                             |
      | Valor Unitário (R$) | Texto    | 200,00                        |

      E clico no botão "Salvar"

      Então vejo mensagem de sucesso "Gasto registrado com sucesso."

      Cenário: Sai do sistema
      Quando acesso o menu "Sair"

      @do_document
      Cenário: Registro da Frequência Diária
      Os membros do projeto registram suas atividades diárias.

      Dado acesso a página "/"
      Quando realizo o login com o usuário "20191101011101" e senha "abcd"
      E a data do sistema for "20/01/2018"
      E clico no link "Título do projeto"
      Então vejo a página "Projeto de Extensão"
      Quando clico na aba "Registros de Frequência/Atividade Diária"
      Então vejo o botão "Cadastrar Frequência/Atividade Diária"
      Quando clico no botão "Cadastrar Frequência/Atividade Diária"
      Então vejo a página "Registrar Frequência/Atividade Diária"
      E vejo os seguintes campos no formulário
      | Campo     | Tipo     |
      | Descrição | TextArea |
      | Data      | Data     |
      E vejo o botão "Salvar"
      Quando preencho o formulário com os dados
      | Campo     | Tipo     | Valor                         |
      | Descrição | TextArea | Descrição da atividade do dia |
      | Data      | Data     | 20/02/2018                    |
      E clico no botão "Salvar"

      Então vejo mensagem de sucesso "Frequência/Atividade diária cadastrada com sucesso."

      Cenário: Sai do sistema
      Quando acesso o menu "Sair"


      @do_document
      Cenário: Alterar data de término do projeto
      Permite a atualização da data de término prevista do projeto.
      Ação executada pelo Servidor (coordenador do projeto).

      Dado acesso a página "/"
      Quando realizo o login com o usuário "110003" e senha "abcd"
      E a data do sistema for "20/01/2018"
      E acesso o menu "Extensão::Projetos::Meus Projetos"
      Então vejo a página "Meus Projetos"
      E vejo o botão "Visualizar"
      Quando clico no botão "Visualizar"
      Então vejo a página "Projeto de Extensão"
      Quando clico na aba "Dados do Projeto"
      Então vejo o botão "Editar Projeto"
      Quando clico no botão "Editar Projeto"
      Então vejo a página "Editar Projeto"
      E vejo os seguintes campos no formulário
      | Campo                               | Tipo     |
      | Término da Execução                 | data    |
      | Justificativa da Alteração de Datas | TextArea |
      E vejo o botão "Salvar"
      Quando preencho o formulário com os dados
      | Campo                               | Tipo     | Valor                             |
      | Término da Execução                 | data     | 30/12/2018                        |
      | Justificativa da Alteração de Datas | TextArea | Atraso na execução das atividades |
E clico no botão "Salvar"

Então vejo mensagem de sucesso "Projeto editado com sucesso."

Cenário: Sai do sistema
Quando acesso o menu "Sair"
