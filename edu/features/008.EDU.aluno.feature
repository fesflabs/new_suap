# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Área do aluno

  Cenário: Configuração inicial para execução dos cenários do EDU
    Dado os cadastros da funcionalidade 001
    E os cadastros da funcionalidade 002
    E os cadastros da funcionalidade 003
    E os cadastros da funcionalidade 004
    E os cadastros da funcionalidade 005
    E os cadastros da funcionalidade 006
    E os cadastros da funcionalidade 007
    E acesso a página "/"
    Quando realizo o login com o usuário "100001" e senha "abcd"
    E a data do sistema for "22/07/2019"

  Cenário: Cadastrar Atividade Complementar
    Quando pesquiso por "Tipos de Atividades Complementares" e acesso o menu "Ensino::Cadastros Gerais::Tipos de Atividades Complementares"
    E clico no botão "Adicionar Tipo de Atividade Complementar"
    E preencho o formulário com os dados
      | Campo                 | Tipo                  | Valor                            |
      | Descrição             | texto                 | Descrição Atividade Complementar |
      | Modalidades de Ensino | autocomplete multiplo | Especialização                   |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  Cenário: Autenticar como Aluno
    Quando acesso o menu "Sair"
    E realizo o login com o usuário "20191101010001" e senha "123"

  @do_document
  Cenário: Verificar Pendências e Avisos
    Quando olho para o quadro "Pendências"
    Entao vejo o texto "Responda ao questionário "

  @do_document
  Cenário: Acessar Disciplina
    Quando pesquiso por "Disciplinas" e acesso o menu "Ensino::Minhas Disciplinas"
    E olho para os filtros
    E preencho o formulário com os dados
      | Campo               | Tipo  | Valor  |
      | Filtrar por período | lista | 2019.2 |
    E olho para a página

  @do_document
  Cenário: Acessar Dados do Aluno
    Dado acesso a página "/"
    Quando olho para o quadro "Ensino"
    E clico no botão "Meus Dados"
    Então vejo a página "João da Silva (20191101010001)"

  @do_document
  Cenário: Adicionar Dados Bancários
    Dado os cadastros iniciais de banco
    Quando clico na aba "Dados Bancários"
    E olho para o quadro "Dados Bancários"
    E clico no botão "Adicionar Dados Bancários"
    E olho para o popup
    E preencho o formulário com os dados
      | Campo             | Tipo         | Valor           |
      | Código            | texto        | 123456          |
    E clico no botão "Autenticar"
    E preencho o formulário com os dados
      | Campo             | Tipo         | Valor           |
      | Banco             | autocomplete | Banco do Brasil |
      | Número da Agência | texto        |          123456 |
      | Tipo da Conta     | lista        | Conta Corrente  |
      | Número da Conta   | texto        |           12345 |
    E clico no botão "Salvar"
    Entao vejo mensagem de sucesso "Dados bancários adicionado com sucesso."
    Quando olho para o quadro "Dados Bancários"

  @do_document
  Cenário: Adicionar Atividade Complementar
    Quando clico na aba "Atividades Complementares"
    E olho para o quadro "Lançamentos"
    E clico no botão "Informar Atividade Complementar"
    E preencho o formulário com os dados
      | Campo             | Tipo    | Valor                            |
      | Ano Letivo        | lista   |                             2019 |
      | Período Letivo    | lista   |                                1 |
      | Vinculação        | radio   | Não curricular                   |
      | Tipo              | lista   | Descrição Atividade Complementar |
      | Atividade         | texto   | Atividade                        |
      | Data da Atividade | Data    | 01/01/2019                       |
      | Carga Horária     | texto   |                               10 |
      | Anexo             | arquivo | arquivo.pdf                      |
    E clico no botão "Salvar"
    Entao vejo mensagem de sucesso "Atividade complementar adicionada com sucesso. Compareça à secretaria acadêmica para entregar fisicamente o documento."

  @do_document
  Cenário: Atualizar Informações do Aluno
    Quando clico no botão "Editar"
    E clico no botão "Dados Pessoais"
    E olho para o popup
    E preencho o formulário com os dados
      | Campo                              | Tipo  | Valor |
      | Utiliza Transporte Escolar Público | lista | Não   |
    E clico no botão "Enviar"
    Então vejo mensagem de sucesso "Dados Pessoais atualizados com sucesso."

  @do_document
  Cenário: Emitir Declarações e Comprovantes
    Quando clico no botão "Documentos"
    Então vejo o botão "Histórico Parcial"
    E vejo o botão "Declaração de Carga Horária Integralizada"
    E vejo o botão "Comprovante de Dados Acadêmicos"
    E vejo o botão "Matriz Curricular"

  @do_document
  Cenário: Consultar Dados Acadêmicos
    O aluno pode conferir seus dados acadêmicos atualizados após processamento dos pedidos de renovação de matrícula.

    Quando clico no link "João Silva"
    E clico na aba "Requisitos de Conclusão"
    E olho para o quadro "Percentual de Progresso no Curso"
    E olho para a página
    E clico na aba "Histórico"
    E olho para o quadro "Componentes Curriculares"
    E olho para a página
    E clico na aba "Boletins"
    E olho para os filtros
    E olho para a página
    E olho para o quadro "Boletim - 2019/2"
    E olho para a página
    E clico na aba "Dados Acadêmicos"
    E olho para o quadro "Matrículas em Períodos"
    E olho para a página
    E olho para o quadro "Dados Acadêmicos"
