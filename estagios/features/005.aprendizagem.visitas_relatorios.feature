# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Cadastros de visitas e relatórios de uma aprendizagem
  pre-requisitos para encerramento da aprendizagem. No final desse teste o estado da aprendizagem passará de "Em Andamento" para "Apto para Conclusão".

  @do_document
  Cenário: O professor orientador cadastra a Visita do módulo
    Dado acesso a página "/"
    Quando realizo o login com o usuário "102003" e senha "abcd"
    E clico no link "Orientações de Estágios e Afins"
    E olho a linha "Aluno"
    E clico no ícone de exibição
    Então vejo a página "Aprendizagem do aluno Aluno Estágio (20191101011021) na concedente Banco do Brasil (00000000000191)"
    Quando clico na aba "Visitas do Orientador"
    E clico no botão "Registrar Visita"
    Quando preencho o formulário com os dados
      | Campo                                          | Tipo     | Valor                            |
      | Data da Visita                                 | Data     | 15/08/2018                       |
      | Ambiente Adequado                              | Checkbox | Marcar                           |
      | Justificativa para Ambiente Inadequado         | TextArea |                                  |
      | Desenvolvimento Atividades Previstas           | Checkbox | Marcar                           |
      | Desenvolvimento Atividades Fora da Competência | Checkbox | Desmarcar                        |
      | Desenvolvimento Atividades Não-Previstas       | Checkbox | Desmarcar                        |
      | Atividades Não-Previstas                       | TextArea |                                  |
      | Apoiado pelo Supervisor                        | Checkbox | Marcar                           |
      | Direitos Respeitados                           | Checkbox | Marcar                           |
      | Especificar direitos não respeitados           | TextArea |                                  |
      | Aprendizagem Satisfatória                      | Checkbox | Marcar                           |
      | Informações Adicionais                         | TextArea | Correu tudo bem na aprendizagem. |
    Quando clico no botão "Salvar"
    Então vejo mensagem de sucesso "Visita adicionada com sucesso."
    Quando clico na aba "Visitas do Orientador"
    Então vejo o texto "Relatório da Visita realizada em 15/08/2018 pendente."
    E vejo o botão "Gerar Relatório da Visita no dia 15/08/2018"
    Quando clico no ícone de edição
    E olho para o popup
    Quando preencho o formulário com os dados
      | Campo               | Tipo    | Valor         |
      | Relatório de Visita | Arquivo | Relatório.pdf |
    Quando clico no botão "Salvar"
    Quando o popup é fechado
    #Então nao vejo o texto "Relatório da Visita realizada em 15/08/2018 pendente."
    Quando acesso o menu "Sair"

  @do_document
  Cenário: O professor orientador cadastra um Agendamento de Orientação da Aprendizagem
    Dado acesso a página "/"
    Quando realizo o login com o usuário "102003" e senha "abcd"
    E clico no link "Orientações de Estágios e Afins"
    E olho a linha "Aluno"
    E clico no ícone de exibição
    Então vejo a página "Aprendizagem do aluno Aluno Estágio (20191101011021) na concedente Banco do Brasil (00000000000191)"
    Quando clico na aba "Atividades de Orientação"
    E clico no botão "Agendar Orientação"
    E olho para o popup
    Então vejo os seguintes campos no formulário
      | Campo                               | Tipo     |
      | Data da Reunião de Orientação       | Data     |
      | Hora de Início                      | Texto    |
      | Local                               | Texto    |
      | Descrição do Conteúdo da Orientação | TextArea |
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
  Cenário: O aprendiz cadastra o relatório do módulo
    Dado acesso a página "/"
    Quando realizo o login com o usuário "20191101011021" e senha "abcd"
    E clico no link "Rel. Atividades Pendentes"
    Quando olho para o quadro "Registros de Aprendizagem"
    Quando clico no ícone de exibição
    Então vejo a página "Aprendizagem do aluno Aluno Estágio (20191101011021) na concedente Banco do Brasil (00000000000191)"
    Quando clico na aba "Relatórios de Atividades – Aprendiz"
    Quando clico no botão "Registrar/Editar Relatório"
    Então vejo a página "Submeter Relatório do Módulo I (de 01/01/2018 até 31/12/2018) - Aprendiz"
    Quando preencho o formulário com os dados
      | Campo                                                                      | Tipo     | Valor                         |
      | Sobre as Atividades                                                        | Lista    | Realizadas                    |
      | Comentários sobre o desenvolvimento das atividades                         | TextArea | Tudo certo com as atividades. |
      | Realizou atividades não previstas no resumo do curso? Informe e justifique | TextArea | Não.                          |
      | Área de Formação                                                           | Lista    | Sim                           |
      | Contribuição da Aprendizagem                                               | Lista    | Sim                           |
      | Aplicação do Conhecimento                                                  | Lista    | Sim                           |
      | Conceito                                                                   | Lista    | Excelente                     |
      | Data do Relatório                                                          | Data     | 15/01/2019                    |
      | Relatório do Módulo                                                        | Arquivo  | Arquivo.pdf                   |
    Quando clico no botão "Salvar"
    Então vejo mensagem de sucesso "Avaliação registrada com sucesso."
    Quando acesso o menu "Sair"

  @do_document
  Cenário: O coordenador de estágio cadastra o relatório de atividades do módulo do empregado monitor
    Dado acesso a página "/"
    Quando realizo o login com o usuário "102002" e senha "abcd"
    E acesso o menu "Extensão::Estágio e Afins::Aprendizagens"
    E olho para a listagem
    E olho a linha "Aluno"
    Quando clico no ícone de exibição
    Então vejo a página "Aprendizagem do aluno Aluno Estágio (20191101011021) na concedente Banco do Brasil (00000000000191)"
    Quando clico na aba "Relatórios de Atividades – Empregado Monitor"
    Quando clico no botão "Registrar/Editar Relatório"
    Então vejo a página "Submeter Relatório do Módulo I (de 01/01/2018 até 31/12/2018) - Empregado Monitor"
    Quando preencho o formulário com os dados
      | Campo                                                                      | Tipo     | Valor                                             |
      | Sobre as Atividades                                                        | Lista    | Realizadas                                        |
      | Comentários sobre o desenvolvimento das atividades                         | TextArea | Tudo certo com as atividades.                     |
      | Realizou atividades não previstas no resumo do curso? Informe e justifique | TextArea | Não.                                              |
      | Nota do Aprendiz                                                           | Lista    |                                                10 |
      | Comentários e Sugestões                                                    | TextArea | Sugiro afiwebnamento com a instituição de ensino. |
      | Data do Relatório                                                          | Data     | 15/01/2019                                        |
      | Relatório do Módulo                                                        | Arquivo  | Arquivo.pdf                                       |
    Quando clico no botão "Salvar"
    Então vejo mensagem de sucesso "Avaliação registrada com sucesso."
    Quando acesso o menu "Extensão::Estágio e Afins::Aprendizagens"
    Quando clico na aba "Apto para Conclusão"
    E olho para a listagem
    Então vejo a linha "Aluno"
    Quando acesso o menu "Sair"
