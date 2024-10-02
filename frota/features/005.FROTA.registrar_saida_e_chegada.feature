# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Registro de Início e de Término da Viagem

      @do_document
      Cenário: Registro da Saída da Viatura
      Informa a data e hora do início da viagem.
      Ação executada pelo Coordenador de Frota Sistêmico ou Coordenador de Frota.
          Dado acesso a página "/"
        Quando realizo o login com o usuário "107001" e senha "abcd"
             E a data do sistema for "25/11/2018"
             E acesso o menu "Administração::Frota::Viagens::Registrar Saída"
         Então vejo a página "Viagens Agendadas"
         Quando clico no botão "Todas as Viaturas"
           E olho a linha "Agendador Frota"
         Então vejo o botão "Registrar Saída"
         Quando clico no botão "Registrar Saída"
         Então vejo a página "Registrar Saída"
             E vejo os seguintes campos no formulário
               | Campo                                         | Tipo     |
               | Data e Hora                                   | Data     |
               | Viatura                                       | Lista    |
               | Motoristas Disponíveis                                | FilteredSelectMultiple    |
               | Odômetro                                      | Texto    |
               | Passageiros                                   | Autocomplete multiplo |

             E vejo o botão "Salvar"

        Quando preencho o formulário com os dados
               | Campo                                         | Tipo     | Valor                                       |
               | Data e Hora                                   | Data     | 03/12/2018                                  |
               | Viatura                                       | Lista    | MXY-0001 Ford Ranger                        |
               | Motoristas Disponíveis                                    | FilteredSelectMultiple    | Motorista      |
               | Odômetro                                      | Texto    | 10000                                       |


             E clico no botão "Salvar"

        Então vejo mensagem de sucesso "Viagem iniciada com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"


       @do_document
      Cenário: Registro da Chegada da Viatura
      Informa a data e hora do término da viagem.
      Ação executada pelo Coordenador de Frota Sistêmico ou Coordenador de Frota.
          Dado acesso a página "/"
        Quando realizo o login com o usuário "107001" e senha "abcd"
             E acesso o menu "Administração::Frota::Viagens::Registrar Chegada"
         Então vejo a página "Viagens Iniciadas"
         Quando clico no botão "Todas as Viaturas"
           E olho a linha "Agendador Frota"
         Então vejo o botão "Registrar Chegada"
         Quando clico no botão "Registrar Chegada"
         Então vejo a página "Registrar Chegada"
             E vejo os seguintes campos no formulário
               | Campo                                         | Tipo     |
               | Data e Hora                                   | Data     |
               | Odômetro                                      | Texto    |

             E vejo o botão "Salvar"

        Quando preencho o formulário com os dados
               | Campo                                         | Tipo     | Valor                                       |
               | Data e Hora                                   | Data     | 04/12/2018                                  |
               | Odômetro                                      | Texto    | 10100                                       |


             E clico no botão "Salvar"

        Então vejo mensagem de sucesso "Viagem finalizada com sucesso."
