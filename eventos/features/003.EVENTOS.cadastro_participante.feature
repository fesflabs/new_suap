# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Cadastro do Participante

  @do_document
  Cenário: Cadastro de Participante do Evento
    Ação executada pelo coordenador do evento.

    Dado acesso a página "/"
    Quando a data do sistema for "01/01/2020"
    Quando realizo o login com o usuário "155001" e senha "abcd"
    E acesso o menu "Comunicação Social::Eventos"
    Então vejo a página "Eventos"
    Quando olho a linha "Nome do Evento"
    E clico no ícone de exibição
    Então vejo a página "Nome do Evento"
    Quando clico na aba "Organizador"
    E olho para o quadro "Organizador"
    E clico no botão "Adicionar"
    E olho para o popup
    Então vejo os seguintes campos no formulário
      | Campo                     | Tipo         |
      | Nome                      | Texto        |
      | CPF                       | Texto        |
      | E-mail                    | Texto        |
      | Perfil                    | Autocomplete |
    E vejo o botão "Salvar"
    Quando preencho o formulário com os dados
      | Campo  | Tipo         | Valor                  |
      | Nome   | Texto        | Nome do Participante   |
      | CPF    | Texto        | 268.058.310-83         |
      | E-mail | Texto        | email@participante.com |
      | Perfil | Autocomplete | Público Externo        |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Organizador adicionado com sucesso."

  Cenário: Sai do sistema
    Quando acesso o menu "Sair"
