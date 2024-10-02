# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Gerenciamento de Frota

      Cenário: Adicionando os usuários necessários para os testes FROTA
          Dado os dados básicos para frota
            E  os seguintes usuários
                | Nome                  | Matrícula | Setor | Lotação | Email                           | CPF            | Senha | Grupo                          |
                | Coord_Frota Sistêmico | 107001    | CZN   | CZN     | coordfrotasistemico@ifrn.edu.br | 645.433.195-40 | abcd  | Coordenador de Frota Sistêmico |
                | Coord_Frota Campus    | 107002    | CZN   | CZN     | coordfrotacampuso@ifrn.edu.br   | 188.135.291-98 | abcd  | Coordenador de Frota           |
                | Agendador Frota       | 107003    | CZN   | CZN     | agendadorfrota@ifrn.edu.br      | 232.607.644-37 | abcd  | Agendador de Frota             |
                | Passageiro Frota      | 107004    | CZN   | CZN     | passageirofrota@ifrn.edu.br     | 568.288.693-38 | abcd  | Servidor                       |
                | Motorista Frota       | 107005    | CZN   | CZN     | motorista@ifrn.edu.br           | 568.288.693-38 | abcd  | Servidor                       |


      @do_document
      Cenário: Cadastro de Viatura
      Cadastro dos veículos que serão utilizados em viagens do Instituto. Caso seja necessário cadastrar veículos sem patrimônio, como é o caso de veículos terceirizados,
      é preciso habilitar esta possibilidade na tela de configurações gerais do SUAP.
      Ação executada pelo Coordenador de Frota Sistêmico ou Coordenador de Frota.
          Dado acesso a página "/"
        Quando realizo o login com o usuário "107002" e senha "abcd"
             E acesso o menu "Administração::Frota::Cadastros::Viaturas"
         Então vejo a página "Viaturas"
             E vejo o botão "Adicionar Viatura"
        Quando clico no botão "Adicionar Viatura"
         Então vejo a página "Adicionar Viatura"
             E vejo os seguintes campos no formulário
               | Campo                          | Tipo     |
               | Patrimônio                     | Autocomplete |
               | Grupo                          | Lista    |
               | Modelo                         | Autocomplete    |
               | Cor                            | Autocomplete    |
               | Ano                            | Texto    |
               | Placa                          | Texto    |
               | Lotação                        | Texto    |
               | Odômetro                       | Texto    |
               | Chassi                         | Texto    |
               | Renavam                        | Texto    |
               | Potência                       | Texto    |
               | Cilindrada                     | Texto    |
               | Combustíveis                   | checkbox multiplo |
               | Tanque                         | Texto    |
               | Rendimento Estimado            | Texto    |

             E vejo o botão "Salvar"

        Quando preencho o formulário com os dados
               | Campo                               | Tipo     | Valor                    |
               | Patrimônio                     | Autocomplete |  123456                   |
               | Grupo                          | Lista        | Carro de Passeio          |
               | Modelo                         | Autocomplete        | Ranger                    |
               | Cor                            | Autocomplete        | Branca                    |
               | Ano                            | Texto        | 2012                      |
               | Placa                          | Texto        | MXY-0001                  |
               | Lotação                        | Texto        | 5                         |
               | Odômetro                       | Texto        | 10000                     |
               | Chassi                         | Texto        | 11111111111111111         |
               | Renavam                        | Texto        | 999999999                 |
               | Potência                       | Texto        | 140                       |
               | Cilindrada                     | Texto        | 1400                      |
               | Combustíveis                   | checkbox multiplo    | Gasolina                  |
               | Tanque                         | Texto        | 50                        |
               | Rendimento Estimado            | Texto        | 10                        |


             E clico no botão "Salvar"

         Então vejo mensagem de sucesso "Cadastro realizado com sucesso."
