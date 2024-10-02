# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Empenhos
    Cadastro de Empenho

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do Almoxarifado
    Dado o cadastro de processo
    Quando acesso a página "/"
    E realizo o login com o usuário "CoordDeAlmoxSiste" e senha "abcd"

  @do_document
  Cenario: Adicionar Empenho
    Dado acesso a página "/"
    Quando acesso a página "/almoxarifado/empenhos"
    E clico no botão "Adicionar Empenho"
    E preencho o formulário com os dados
        | Campo                  | Tipo         | Valor                    |
        | Número de empenho      | Texto        | 2019NE123456             |
        | Processo               | Autocomplete | Assunto Teste            |
        | Tipo de Material       | Autocomplete | Consumo                  |
        | Pessoa Física          | Autocomplete | CoordDeAlmoxSiste        |
    E clico no botão "Salvar"
    E clico no botão "Empenhar Novo Item"
    E preencho o formulário com os dados
        | Campo                  | Tipo         | Valor      |
        | Material               | Autocomplete | 000001     |
        | Qtd. Empenhada         | Texto        | 2          |
        | Valor Unitário         | Texto        | 200        |
        | Continuar cadastrando  | checkbox     | desmarcar  |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Item de Empenho cadastrada com sucesso."

  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"
