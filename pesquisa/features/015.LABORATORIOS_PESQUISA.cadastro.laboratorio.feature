# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro do Laboratório de Pesquisa

      @do_document
      Cenário: Cadastro do Laboratório de Pesquisa
      Cadastro de laboratório de pesquisa.
      Ação executada pelo Diretor de Pesquisa ou Asessor de Pesquisa.
          Dado acesso a página "/"
          E os ajustes para o laboratório
        Quando realizo o login com o usuário "108001" e senha "abcd"
        E acesso o menu "Pesquisa::Laboratórios::Laboratórios"
        Então vejo a página "Laboratórios de Pesquisa"
        E vejo o botão "Adicionar Laboratório"
        Quando clico no botão "Adicionar Laboratório"
         Então vejo a página "Adicionar Laboratório de Pesquisa"
             E vejo os seguintes campos no formulário
               | Campo              | Tipo     |
               | Nome               | Texto    |
               | Coordenador        | Autocomplete    |
               | Campus             | Lista    |
               | Descrição          | TextArea |
               | Área de Pesquisa   | Autocomplete    |
               | Membros            | Autocomplete Multiplo |

             E vejo o botão "Salvar"


        Quando preencho o formulário com os dados
               | Campo              | Tipo     | Valor                 |
               | Nome               | Texto    | Nome do Laboratório   |
               | Coordenador        | Autocomplete    | 108013 |
               | Campus             | Lista    | CZN |
               | Descrição          | TextArea | Descrição e características do laboratório |
               | Área de Pesquisa   | Autocomplete    | BIOQUÍMICA |
               | Membros            | Autocomplete Multiplo | 108014 |


             E clico no botão "Salvar"

         Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"

       @do_document
      Cenário: Cadastro de Finalidade de Serviço do Laboratório de Pesquisa
      Ação executada pelo Diretor de Pesquisa ou Asessor de Pesquisa
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108001" e senha "abcd"
        E acesso o menu "Pesquisa::Laboratórios::Cadastros::Finalidade"
        Então vejo a página "Tipos de Finalidade do Serviço"
        Quando clico no botão "Adicionar Tipo de Finalidade do Serviço"
         Então vejo a página "Adicionar Tipo de Finalidade do Serviço"

             E vejo os seguintes campos no formulário
                 | Campo                             | Tipo         |
                 | Descrição                         | Texto        |

                 E vejo o botão "Salvar"
          Quando preencho o formulário com os dados
               | Campo                          | Tipo            | Valor                                     |
               | Descrição                         | Texto        | Análise de amostra para projeto de pesquisa |

             E clico no botão "Salvar"
         Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"

      @do_document
      Cenário: Cadastro de Equipamentos do Laboratório de Pesquisa
      Ação executada pelo Coordenador do Laboratório de Pesquisa
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108013" e senha "abcd"
        E acesso o menu "Pesquisa::Laboratórios::Laboratórios"
        Então vejo a página "Laboratórios de Pesquisa"
        Quando clico no botão "Visualizar"
         Então vejo a página "Nome do Laboratório"
         Quando clico na aba "Equipamentos"
         Então vejo o botão "Adicionar Equipamento"
          Quando clico no botão "Adicionar Equipamento"
             Então vejo os seguintes campos no formulário
                 | Campo                             | Tipo         |
                 | Nome                              | Texto        |
                 | Descrição                         | TextArea        |
                 | Inventário                        | Autocomplete |
                 E vejo o botão "Salvar"
          Quando preencho o formulário com os dados
               | Campo                          | Tipo         | Valor                                    |
               | Nome                              | Texto        | Equipamento do Laboratório  |
                 | Descrição                         | TextArea        | Descrição do equipamento |
                 | Inventário                        | Autocomplete | 123455 |
             E clico no botão "Salvar"
         Então vejo mensagem de sucesso "Equipamento cadastrado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"

       @do_document
      Cenário: Cadastro de Serviços do Laboratório de Pesquisa
      Ação executada pelo Coordenador do Laboratório de Pesquisa
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108013" e senha "abcd"
        E acesso o menu "Pesquisa::Laboratórios::Laboratórios"
        Então vejo a página "Laboratórios de Pesquisa"
        Quando clico no botão "Visualizar"
         Então vejo a página "Nome do Laboratório"
         Quando clico na aba "Serviços"
         Então vejo o botão "Adicionar Serviço"
          Quando clico no botão "Adicionar Serviço"
             Então vejo os seguintes campos no formulário
                 | Campo                             | Tipo         |
                 | Descrição                         | TextArea     |
                 | Materiais Utilizados              | TextArea        |
                 | Equipamentos Utilizados           | FilteredSelectMultiple |
                 E vejo o botão "Salvar"
          Quando preencho o formulário com os dados
               | Campo                          | Tipo         | Valor                                    |
               | Descrição                         | TextArea     | Descrição do Serviço realizado pelo Laboratório |
               | Materiais Utilizados              | TextArea        | Detalhamento do material utilizado |
               | Equipamentos Utilizados           | FilteredSelectMultiple |  Descrição do equipamento |
             E clico no botão "Salvar"
         Então vejo mensagem de sucesso "Serviço cadastrado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"


       @do_document
      Cenário: Cadastro de Materiais do Laboratório de Pesquisa
      Ação executada pelo Coordenador do Laboratório de Pesquisa
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108013" e senha "abcd"
        E acesso o menu "Pesquisa::Laboratórios::Laboratórios"
        Então vejo a página "Laboratórios de Pesquisa"
        Quando clico no botão "Visualizar"
         Então vejo a página "Nome do Laboratório"
         Quando clico na aba "Materiais"
         Então vejo o botão "Adicionar Material"
          Quando clico no botão "Adicionar Material"
             Então vejo os seguintes campos no formulário
                 | Campo                             | Tipo         |
                 | Não encontrei o material na lista. Quero cadastrar o novo material.   | Checkbox     |
                 | Descrição             | TextArea        |
                 | Quantidade em Estoque     | Texto |
                 | Valor Unitário (R$)      | Texto |
                 E vejo o botão "Salvar"
          Quando preencho o formulário com os dados
               | Campo                          | Tipo         | Valor                             |
               | Não encontrei o material na lista. Quero cadastrar o novo material.   | Checkbox  | marcar |
               | Descrição             | TextArea        | Descrição do material existente |
               | Quantidade em Estoque     | Texto | 10 |
               | Valor Unitário (R$)      | Texto |  50 |
             E clico no botão "Salvar"
         Então vejo mensagem de sucesso "Material cadastrado com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"


      @do_document
      Cenário: Solicitar realização de Serviço no Laboratório de Pesquisa
      Ação executada por um coordenador de projeto de pesquisa
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108003" e senha "abcd"
        E acesso o menu "Pesquisa::Laboratórios::Laboratórios"
        Então vejo a página "Laboratórios de Pesquisa"
        Quando clico no botão "Visualizar"
         Então vejo a página "Nome do Laboratório"

          Quando clico no botão "Solicitar Serviço"
             Então vejo os seguintes campos no formulário
                 | Campo                             | Tipo         |
                 | Serviço   | Autocomplete     |
                 | Finalidade do Serviço             | Autocomplete        |
                 | Data     | Data |
                 | Hora de Início      | Hora |
                 | Hora de Término      | Hora |
                 | Descrição do Serviço | TextArea |
                 E vejo o botão "Salvar"
          Quando preencho o formulário com os dados
                 | Campo                          | Tipo         | Valor                             |
                 | Serviço   | Autocomplete     | Descrição do Serviço realizado pelo Laboratório |
                 | Finalidade do Serviço             | Autocomplete     | Análise de amostra para projeto de pesquisa |
                 | Data     | Data |     30/05/2022 |
                 | Hora de Início      | Hora | 10:00:00 |
                 | Hora de Término      | Hora | 12:00:00 |
                 | Descrição do Serviço | TextArea | Descrição detalhada sobre a realização do serviço |
             E clico no botão "Salvar"
         Então vejo mensagem de sucesso "Solicitação de serviço cadastrada com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"


      @do_document
      Cenário: Avaliar solicitação de Serviço no Laboratório de Pesquisa
      Ação executada pelo coordenador do laboratório
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108013" e senha "abcd"
        E acesso o menu "Pesquisa::Laboratórios::Laboratórios"
        Então vejo a página "Laboratórios de Pesquisa"
        Quando clico no botão "Visualizar"
         Então vejo a página "Nome do Laboratório"
        Quando clico na aba "Solicitações de Serviço"
         Então vejo o botão "Aprovar"
          Quando clico no botão "Aprovar"
          E olho para o popup


             Então vejo os seguintes campos no formulário
                 | Campo                             | Tipo         |
                 | Resposta   | TextArea     |

                 E vejo o botão "Salvar"
          Quando preencho o formulário com os dados
                 | Campo                          | Tipo         | Valor                             |
                 | Resposta   | TextArea     | Declaração de aceite com orientações |
             E clico no botão "Salvar"
         Então vejo mensagem de sucesso "Solicitação avaliada com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"



       @do_document
      Cenário: Acompanhamento da solicitação de Serviço no Laboratório de Pesquisa
      Ação executada pelo coordenador do laboratório
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108003" e senha "abcd"
        E acesso o menu "Pesquisa::Laboratórios::Minhas Solicitações"
        Então vejo a página "Minhas Solicitações de Serviço"
          Quando clico no botão "Acompanhar Solicitação"
          Então vejo a página "Acompanhar Solicitação"

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"


       @do_document
      Cenário: Registrar conclusão de Serviço no Laboratório de Pesquisa
      Ação executada pelo coordenador do laboratório
          Dado acesso a página "/"
        Quando realizo o login com o usuário "108013" e senha "abcd"
        E acesso o menu "Pesquisa::Laboratórios::Laboratórios"
        Então vejo a página "Laboratórios de Pesquisa"
        Quando clico no botão "Visualizar"
         Então vejo a página "Nome do Laboratório"
         Quando clico na aba "Solicitações de Serviço"
         Então vejo o botão "Registrar Conclusão"
         Quando clico no botão "Registrar Conclusão"
         Então vejo mensagem de sucesso "Solicitação concluída com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"
