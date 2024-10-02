# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Cadastros de visitas e relatórios semestrais

  pre-requisitos para o encerramento do estágio. No final
  desse teste o estado do estágio passará de "Em Andamento"
  para "Apto para Encerramento".

  @do_document
  Cenário: O professor orientador cadastra a Visita
    Dado acesso a página "/"
    Quando realizo o login com o usuário "102004" e senha "abcd"
    Então vejo o quadro "Professores"
    Quando clico no link "Orientações de Estágios e Afins"
    E olho a linha "Aluno"
    E clico no ícone de exibição
    Então vejo a página "Estágio de Aluno Estágio (20191101011021) em BANCO DO BRASIL SA (00.000.000/0001-91)"
    Quando clico na aba "Visitas do Orientador"
    E clico no botão "Adicionar Visita"
    Quando preencho o formulário com os dados
      | Campo                                          | Tipo     | Valor                       |
      | Data da Visita                                 | Data     | 15/08/2018                  |
      | Ambiente Adequado                              | Checkbox | Marcar                      |
      | Justificativa para Ambiente Inadequado         | TextArea |                             |
      | Desenvolvimento Atividades Previstas           | Checkbox | Marcar                      |
      | Desenvolvimento Atividades Fora da Competência | Checkbox | Desmarcar                   |
      | Desenvolvimento Atividades Não-Previstas       | Checkbox | Desmarcar                   |
      | Atividades Não-Previstas                       | TextArea |                             |
      | Apoiado pelo Supervisor                        | Checkbox | Marcar                      |
      | Direitos Respeitados                           | Checkbox | Marcar                      |
      | Especificar direitos não respeitados           | TextArea |                             |
      | Aprendizagem Satisfatória                      | Checkbox | Marcar                      |
      | Informações Adicionais                         | TextArea | Correu tudo bem no estágio. |
    Quando clico no botão "Salvar"
    Então vejo mensagem de sucesso "Visita adicionada com sucesso."
    Quando clico na aba "Visitas do Orientador"
    Então vejo o texto "Relatório da Visita realizada em 15/08/2018 pendente."
    E vejo o botão "Gerar Relatório da Visita no dia 15/08/2018"
    Quando olho para a página
    Quando olho para o quadro "Visitas do Orientador"
    Quando clico no ícone de edição
    E olho para o popup
    Quando preencho o formulário com os dados
      | Campo               | Tipo    | Valor         |
      | Relatório de Visita | Arquivo | Relatório.pdf |
    Quando clico no botão "Salvar"
    Então vejo o texto "Relatório da Visita realizada em 15/08/2018 preenchido."
    E vejo mensagem de sucesso "Visita adicionada com sucesso."

  @do_document
  Cenário: O professor orientador cadastra um Agendamento de Orientação de Estágio
    Quando clico na aba "Atividades de Orientação"
    Então vejo o botão "Agendar Orientação"
    Quando clico no botão "Agendar Orientação"
    E olho para o popup
    Quando preencho o formulário com os dados
      | Campo                               | Tipo     | Valor                                               |
      | Hora de Início                      | Texto    | 14:00                                               |
      | Local                               | Texto    | Sala C10                                            |
      | Descrição do Conteúdo da Orientação | TextArea | Tirar dúvidas e orietações relacionadas ao estágio. |
      | Data da Reunião de Orientação       | Data     | 16/08/2018                                          |
    Quando clico no botão "Salvar"
    Então vejo mensagem de sucesso "Agendamento de orientação adicionado com sucesso."
    Quando acesso o menu "Sair"

  @do_document
  Cenário: O estagiário cadastra o relatório semestral
    Quando a data do sistema for "01/10/2018"
    E realizo o login com o usuário "20191101011021" e senha "abcd"
    E clico no link "Rel. Atividades Pendentes"
    E clico no botão "Registrar Relatório"
    Então vejo a página "Submeter Relatório Semestral do Aluno"
    Quando preencho o formulário com os dados
      | Campo                                                     | Tipo     | Valor                                 |
      | Período                                                   | Lista    | [01/07/2018 até 30/09/2018]           |
      | Data do Relatório                                         | Data     | 01/10/2018                            |
      | Atividade 1                                               | Lista    | Realizada                             |
      | Atividade 2                                               | Lista    | Realizada                             |
      | Atividade 3                                               | Lista    | Realizada                             |
      | Comentários sobre o desenvolvimento das atividades        | TextArea | Tudo certo com as atividades.         |
      | Realizou atividades não previstas no Plano de Atividades? | Checkbox | Marcar                                |
      | Em caso afirmativo, descreva as atividades                | TextArea | Atividades 4, 5, 6                    |
      | Em caso afirmativo, justifique                            | TextArea | Surgiram novas possibilidades.        |
      | Área de Formação                                          | Lista    | Sim                                   |
      | Contribuição do Estágio                                   | Lista    | Sim                                   |
      | Aplicação do Conhecimento                                 | Lista    | Sim                                   |
      | Conceito                                                  | Lista    | Excelente                             |
      | Comentários e Sugestões                                   | TextArea | Sugiro aconselhamentos ao estágiario. |
      | Relatório Semestral                                       | Arquivo  | Arquivo.pdf                           |
    Quando clico no botão "Salvar"
    Então vejo mensagem de sucesso "Avaliação registrada com sucesso."
    Quando acesso o menu "Sair"

  @do_document
  Cenário: O coordenador de estágio cadastra o relatório semestral do supervisor
    Quando realizo o login com o usuário "102002" e senha "abcd"
    E acesso o menu "Extensão::Estágio e Afins::Estágios"
    Quando clico na aba "Apto para Encerramento"
    #Então vejo mensagem de alerta "Nenhum Estágio encontrado."
    Quando clico na aba "Pendência de Relatório de Atividades do Supervisor"
    E olho para a listagem
    E olho a linha "Aluno"
    Quando clico no ícone de exibição
    Então vejo a página "Estágio de Aluno Estágio (20191101011021) em BANCO DO BRASIL SA (00.000.000/0001-91)"
    Quando clico na aba "Relatórios de Atividades - Supervisor"
    E clico no botão "Registrar Relatório"
    Então vejo a página "Registro da Avaliação do Supervisor - Estágio de Aluno Estágio (20191101011021) em BANCO DO BRASIL SA (00.000.000/0001-91)"
    Quando preencho o formulário com os dados
      | Campo                                                     | Tipo     | Valor                          |
      | Período                                                   | Lista    | [01/07/2018 até 30/09/2018]    |
      | Data do Relatório                                         | Data     | 01/10/2018                     |
      | Atividade 1                                               | Lista    | Realizada                      |
      | Atividade 2                                               | Lista    | Realizada                      |
      | Atividade 3                                               | Lista    | Realizada                      |
      | Comentários sobre o desenvolvimento das atividades        | TextArea | Tudo feito corretamente.       |
      | Realizou atividades não previstas no Plano de Atividades? | Checkbox | Marcar                         |
      | Em caso afirmativo, descreva as atividades                | TextArea | Atividades 4, 5, 6             |
      | Em caso afirmativo, justifique                            | TextArea | Surgiram novas possibilidades. |
      | Nota do Estagiário                                        | Lista    |                             10 |
      | Relatório Semestral                                       | Arquivo  | Arquivo.pdf                    |
    Quando clico no botão "Salvar"
    Então vejo mensagem de sucesso "Avaliação do supervisor registrada com sucesso."
    Quando acesso o menu "Extensão::Estágio e Afins::Estágios"
    Quando clico na aba "Apto para Encerramento"
    #Então nao vejo mensagem de alerta "Nenhum Estágio encontrado."
    Quando acesso o menu "Sair"
