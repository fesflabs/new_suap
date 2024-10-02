# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Consultar Contratos
  Visando dar maior transparência ao cidadão todos os contratos firmados pela instituição podem ser acompanhados
  internamente pelo SUAP assim como em sua consulta pública.

  @do_document
  Cenário: Consultar Contratos Tela Pública
    Quando acesso o menu "Contratos"
    E olho para a tabela
    E olho a linha "01/2020"
    E clico no link "01/2020"
    Então vejo a página "01/2020"
    E vejo o botão "Arquivo do Contrato"
