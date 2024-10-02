# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Solicitação de Agendamento de Viagem

      @do_document
      Cenário: Solicitação de Agendamento de Viagem
      Permite que o servidor solicite o agendamento de uma viagem.
      Ação executada pelo Operador de Frota ou Agendador de Frota.
          Dado acesso a página "/"
        Quando realizo o login com o usuário "107003" e senha "abcd"
             E acesso o menu "Administração::Frota::Agendamentos"
         Então vejo a página "Agendamentos de Viagens"
             E vejo o botão "Adicionar Agendamento de Viagem"
        Quando clico no botão "Adicionar Agendamento de Viagem"
             E a data do sistema for "25/11/2018"
         Então vejo a página "Adicionar Agendamento de Viagem"
             E vejo os seguintes campos no formulário
               | Campo                          | Tipo     |
               | Objetivo                       | TextArea |
               | Itinerário                     | TextArea |
               | Saída                          | Data |
               | Chegada                        | Data |
               | Nome do Responsável            | Texto    |
               | Telefone do Responsável        | Texto    |
               | Passageiros                    | Autocomplete Multiplo    |
               | Turma                          | Autocomplete Multiplo    |
               | Diário                         | Autocomplete Multiplo    |
               | Alunos                         | Texto    |
               | Local de Saída                 | Texto    |
               | Quantidade de Diárias          | Texto    |
               | Interessados                   | Autocomplete Multiplo    |


             E vejo o botão "Salvar"

        Quando preencho o formulário com os dados
            | Campo                   | Tipo                  | Valor                     |
            | Objetivo                | TextArea              | objetivo da viagem        |
            | Itinerário              | TextArea              | trajeto a ser percorrido  |
            | Saída                   | Data              | 03/12/2018                |
            | Chegada                 | Data              | 04/12/2018                |
            | Nome do Responsável     | Texto                 | Nome do Servidor 1        |
            | Telefone do Responsável | Texto                 | (84) 12345-6789           |
            | Passageiros             | Autocomplete Multiplo | 107004                    |
            | Local de Saída          | Texto                 | local de saída da viatura |


             E clico no botão "Salvar"

         Então vejo mensagem de sucesso "Cadastro realizado com sucesso."
