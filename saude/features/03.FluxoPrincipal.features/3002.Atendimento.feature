# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Agenda de Atendimentos
  Permite que os profissionais de saúde registrem seus horários de atendimento

  # Criando agendamento via perfil do atendente.
  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    E os seguintes campi
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"

  @do_document
  Cenário: Adicionar Agendamento
  Cadastro de horários de atenfimentos
  Ação executada pelo Coordenador de Saúde Sistêmico.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Agenda de Atendimentos"
    E clico no botão "Adicionar Data de Atendimento"
    E preencho o formulário com os dados
      | Campo                                   | Tipo  | Valor               |
      | Especialidade                           | Lista | Avaliação Biomédica |
      | Data Inicial                            | Data  | 25/01/2019          |
      | Horário de Início                       | Hora  | 08:00               |
      | Horário de Término                      | Hora  | 12:00               |
      | Duração de cada atendimento (em minutos | Texto | 30                  |
    E clico no botão "Gerar Horários"
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Horário(s) de atendimento(s) registrado(s) com sucesso."

  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"


  # Selecionando agendamento via perfil do aluno.
  @do_document
  Cenário: Reserva de horário de atendimento
  Selecionar e efetuar o agendamento em um horário disponível.
  Ação executada pelo Aluno.
    Dado os usuarios do SAUDE
    E  os seguintes usuários
      | Nome        | Matrícula      | Setor | Lotação | Email              | CPF            | Senha | Grupo |
      | Aluno Teste | 20191101011111 | CZN   | CZN     | aluno1@ifrn.edu.br | 559.454.350-31 | abcd  | Aluno |
    E os seguintes campi
    E acesso a página "/"
    Quando realizo o login com o usuário "20191101011111" e senha "abcd"
    E a data do sistema for "21/01/2019"
    E acesso o menu "Saúde::Agenda de Atendimentos"
    Então vejo a página "Agenda de Atendimentos"
    E vejo mais de 0 resultados na tabela
    Quando olho a linha "1"
    E clico no botão "Agendar"
    Então vejo mensagem de sucesso "Horário de atendimento agendado com sucesso."

  @do_document
  Cenário: Buscar Agenda de Atendimentos
  Consultar a agenda de atendimentos.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Agenda de Atendimentos"
    Quando preencho o formulário com os dados
      | Campo         | Tipo  | Valor               |
      | Campus        | Lista | CZN                 |
      | Especialidade | Lista | Avaliação Biomédica |
      | Data Inicial  | Data  | 21/01/2019          |
      | Data Final    | Data  | 25/01/2019          |
    E clico no botão "Enviar"
    Então vejo mais de 0 resultados na tabela


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"
