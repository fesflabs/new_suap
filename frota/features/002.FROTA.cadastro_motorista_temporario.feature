# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro de Motorista Temporário
      @do_document
      Cenário: Cadastro de Motorista Temporário
      Cadastro dos servidores e dos funcionários terceirizados que possuem portaria de autorização para conduzirem os veículos.
      Ação executada pelo Coordenador de Frota Sistêmico ou Coordenador de Frota.
          Dado acesso a página "/"
        Quando realizo o login com o usuário "107002" e senha "abcd"
             E acesso o menu "Administração::Frota::Motoristas Temporários"
         Então vejo a página "Motoristas Temporários"
             E vejo o botão "Adicionar Motorista"
        Quando clico no botão "Adicionar Motorista"
         Então vejo a página "Adicionar Motorista Temporário"
             E vejo os seguintes campos no formulário
               | Campo                          | Tipo     |
               | Pessoa                        | Autocomplete |
               | Portaria                       | Texto    |
               | Ano da Portaria                | Texto    |
               | Data Inicial                   | Data     |


             E vejo o botão "Salvar"

        Quando preencho o formulário com os dados
            | Campo           | Tipo         | Valor      |
            | Pessoa          | Autocomplete | 107005     |
            | Portaria        | Texto        | 1234       |
            | Ano da Portaria | Texto        | 2018       |
            | Data Inicial    | Data         | 01/01/2018 |


             E clico no botão "Salvar"

         Então vejo mensagem de sucesso "Cadastro realizado com sucesso."
