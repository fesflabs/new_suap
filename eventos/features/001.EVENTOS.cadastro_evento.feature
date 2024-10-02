# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Cadastro de Evento

  Cenário: Adicionando os usuários necessários para os testes EVENTOS
    Dado os dados básicos para eventos
    E os seguintes usuários
      | Nome             | Matrícula | Setor | Lotação | Email                        | CPF            | Senha | Grupo                    |
      | Coord Evento     | 155001    | CZN   | CZN     | coord_evento@ifrn.edu.br     | 645.433.195-40 | abcd  | Servidor                 |
      | Avaliador Evento | 155002    | CZN   | CZN     | avaliador_evento@ifrn.edu.br | 188.135.291-98 | abcd  | Secretário Acadêmico |

  @do_document
  Cenário: Cadastro de Evento
  Cadastro de um evento.
  Ação executada por um Servidor.

    Dado acesso a página "/"
    Quando a data do sistema for "01/01/2020"
    E realizo o login com o usuário "155001" e senha "abcd"
    E acesso o menu "Comunicação Social::Eventos"
    Então vejo a página "Eventos"
    E vejo o botão "Adicionar Evento"
    Quando clico no botão "Adicionar Evento"
    Então vejo a página "Adicionar Evento"
    E vejo o botão "Salvar"
    Quando preencho o formulário com os dados
      | Campo                         | Tipo                  | Valor                   |
      | Nome                          | Texto                 | Nome do Evento          |
      | Dimensões                     | checkbox multiplo     | Ensino, Pesquisa        |
      | Apresentação                  | Textarea              | Descrição do evento     |
      | Imagem                        | Arquivo Real          | arquivo.png             |
      | Carga Horária                 | Texto                 | 30                      |
      | Site                          | Texto                 | htttp://site.url        |
      | Local                         | Texto                 | Local do Evento         |
      | Início das Inscrições         | Data                 | 01/01/2020              |
      | Hora de Início das Inscrições | Hora                 | 08:00                   |
      | Fim das Inscrições            | Data                 | 31/01/2020              |
      | Hora de Fim das Inscrições    | Hora                 | 18:00                   |
      | Data de Início                | Data                 | 01/02/2020              |
      | Hora de Início                | Hora                 | 08:00                   |
      | Data de Fim                   | Data                  | 10/02/2020              |
      | Hora de Fim                   | Hora                 | 18:00                   |
      | Organizadores                 | Autocomplete multiplo | Coord Evento            |
      | Inscrição Online              | checkbox              | marcar                  |
      | Gera Certificado?             | checkbox              | marcar                  |
      | Localização                   | radio                 | Local                   |
      | Espacialidade                 | radio                 | Ambiente Virtual        |
      | Porte                         | radio                 | Pequeno Porte           |
      | Tipo                          | radio                 | Científico/tecnológico  |
      | Subtipo                       | radio                 | Palestras               |
      | Público Alvo                  | checkbox multiplo     | Público Externo         |
      | Carga Horária                 | Texto                 | 10:00                      |
      | Recursos Envolvidos           | Texto                 | 5.000,00                |
    E preencho as linhas do quadro "Tipos de Participante" com os dados
      | Tipo de Participação:Autocomplete | Limite de Inscrições:Numero | Modelo de Certificado:Arquivo |
      | Participante                      | 50                          | modelo.png                    |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Ação realizada com sucesso."

  Cenário: Sai do sistema
    Quando acesso o menu "Sair"
