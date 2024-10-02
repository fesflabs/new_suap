# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Avaliação da Solicitação de Agendamento de Viagem
      @do_document
      Cenário: Avaliação do Agendamento
      Permite realizar a avaliação da solicitação de agendamento, informando, em caso de aprovação, qual será a viatura utilizada e os motoristas indicados para a realização da viagem.
      Ação executada pelo Coordenador de Frota Sistêmico ou Coordenador de Frota.
          Dado acesso a página "/"
        Quando realizo o login com o usuário "107002" e senha "abcd"
             E a data do sistema for "25/11/2018"
             E acesso o menu "Administração::Frota::Agendamentos"
         Então vejo a página "Agendamentos de Viagens"
             E vejo a aba "Agendamentos Futuros"
        Quando clico na aba "Agendamentos Futuros"
         Então vejo o botão "Avaliar"
         Quando clico no botão "Avaliar"
         Então vejo a página "Avaliação de Agendamento"
             E vejo os seguintes campos no formulário
               | Campo                                                      | Tipo     |
               | Situação                                                   | Lista    |
               | Viaturas Disponíveis                                       | Lista    |
               | Motoristas Disponíveis                                     | FilteredSelectMultiple    |
               | Local de Saída                                             | Texto    |
               | Observações                                                | TextArea |

             E vejo o botão "Salvar"

        Quando preencho o formulário com os dados
            | Campo                  | Tipo                   | Valor                           |
            | Situação               | Lista                  | Deferida                        |
            | Viaturas Disponíveis   | Lista                  | MXY-0001 Ford Ranger            |
            | Motoristas Disponíveis | FilteredSelectMultiple | 107005                          |
            | Observações            | TextArea               | Observações sobre o agendamento |

             E clico no botão "Salvar"

        Então vejo mensagem de sucesso "Agendamento avaliado com sucesso."
