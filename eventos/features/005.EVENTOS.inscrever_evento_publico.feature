# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Inscrever-se em página pública do evento
      @do_document
      Cenário: Usuário acessa página pública para se inscrever em evento.
          Dado acesso a página "/"
        Quando a data do sistema for "10/01/2020"
             E clico no link "Realizar Inscrição em Evento"
         Então vejo a página "Realizar Inscrição em Evento"
        Quando clico no botão "Realizar Inscrição"
         Então vejo a página "Nome do Evento"
             E vejo os seguintes campos no formulário
          | Campo       | Tipo     |
          | Nome        | Texto    |
          | E-mail      | Texto    |
          | Telefone    | Texto    |
          | CPF         | Texto    |
          | Perfil      | Lista    |
          | Verificação | captcha  |
             E vejo o botão "Enviar"
        Quando preencho o formulário com os dados
          | Campo       | Tipo     | Valor            |
          | Nome        | Texto    | Usário Teste     |
          | E-mail      | Texto    | teste@teste.com  |
          | Telefone    | Texto    | (84) 99999-99999 |
          | CPF         | Texto    | 999.999.999-99   |
          | Perfil      | Lista    | Público Externo  |
          | Verificação | captcha  |                  |
             E clico no botão "Enviar"
         Então vejo mensagem de sucesso "Inscrição realizada com sucesso. O comprovante de inscrição será enviado para o e-mail informado assim que a inscrição for confirmada."
