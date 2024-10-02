# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Confirmar Inscrição do Participante

  @do_document
  Cenário: Confirmação de Inscrição do Participante do Evento
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
    E seleciono o custom checkbox "Nome do Participante"
    E clico no botão "Confirmar Inscrição"
    Então vejo mensagem de sucesso "Nenhuma inscrição confirmada."

    Quando clico na aba "Organizador"
    E seleciono o custom checkbox "Nome do Participante"
    E clico no botão "Confirmar Presença"
    Então vejo mensagem de sucesso "1 presença(s) confirmada(s) com sucesso."

    Quando clico na aba "Organizador"
    E seleciono o custom checkbox "Nome do Participante"
    E clico no botão "Enviar Certificado"
    Então vejo mensagem de sucesso "1 E-mail(s) enviado(s) com sucesso."

  Cenário: Sai do sistema
    Quando acesso o menu "Sair"
