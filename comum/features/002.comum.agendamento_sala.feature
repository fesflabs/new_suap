# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Agendamento de Sala
Cadastro de Prédios e Salas

Contexto: Acessa a index da aplicação
Dado acesso a página "/"

Cenário: Efetuar login no sistema
Quando realizo o login com o usuário "admin" e senha "abc"

@do_document
Cenário: Cadastrar prédios
Quando acesso o menu "Administração::Prédios e Salas::Prédios"
Então vejo o botão "Adicionar Prédio"
Quando clico no botão "Adicionar Prédio"
Então vejo a página "Adicionar Prédio"
Quando preencho o formulário com os dados
| Campo  | Tipo         | Valor    |
| Nome   | Texto        | Predio 1 |
| Campus | AutoComplete | A0       |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

Cenário: Realizar o cadastro e atualização de Prédio
Quando acesso o menu "Administração::Prédios e Salas::Prédios"
E clico no botão "Adicionar Prédio"
E preencho o formulário com os dados
| Campo  | Tipo         | Valor    |
| Nome   | Texto        | Predio 2 |
| Campus | AutoComplete | A0       |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."
Quando olho para a listagem
E olho a linha "Predio 2"
E clico no link "Predio 2"
Então vejo a página "Editar Predio 2"
Quando preencho o formulário com os dados
| Campo | Tipo     | Valor     |
| Ativo | Checkbox | Desmarcar |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Atualização realizada com sucesso."

@do_document
Cenário: Cadastrar salas
Quando acesso o menu "Administração::Prédios e Salas::Salas"
Então vejo o botão "Adicionar Sala"
Quando clico no botão "Adicionar Sala"
Então vejo a página "Adicionar Sala"
Quando preencho o formulário com os dados
| Campo                      | Tipo                  | Valor      |
| Nome                       | Texto                 | Sala 1     |
| Prédio                     | Autocomplete          | Predio 1   |
| Avaliadores de Agendamento | Autocomplete Multiplo | Servidor 1 |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."
