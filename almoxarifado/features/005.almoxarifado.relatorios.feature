# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Relatorios
    Relatórios de balancete de Material de Consumo e Materiais Transferidos.

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do Almoxarifado
    Quando acesso a página "/"

  @do_document
  Cenario: Relatório Balancete de Material de Consumo
    Dado acesso a página "/"
    Quando realizo o login com o usuário "CoordDeAlmoxSiste" e senha "abcd"
    Quando acesso a página "/almoxarifado/balancete_ed_detalhado/"
    E preencho o formulário com os dados
        | Campo                | Tipo     | Valor                          |
        | Elemento de despesa  | Lista    | 30021 - Novo Teste Elemento    |
        | Data inicial         | Data     | 07/05/2019                     |
        | Data final           | Data     | 07/05/2019                     |
    E clico no botão "Enviar"
    Então vejo mensagem de sucesso "Balancete Elemento de Despesa Detalhado"

  @do_document
  Cenario: Relatório de Materiais Transferidos
    Quando acesso a página "/almoxarifado/materiais_transferidos/"
    E preencho o formulário com os dados
        | Campo                | Tipo         | Valor             |
        | Solicitante          | Autocomplete | CoordDeAlmoxSiste |
        | Data inicial         | Data         | 13/05/2019        |
        | Data final           | Data         | 13/05/2019        |
    E clico no botão "Enviar"
    Então vejo a página "Materiais Transferidos"
