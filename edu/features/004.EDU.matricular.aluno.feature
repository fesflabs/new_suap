# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Matricular Aluno

  Cenário: Configuração inicial para execução dos cenários do edu
    Dado os cadastros da funcionalidade 001
    E os cadastros da funcionalidade 002
    E os cadastros da funcionalidade 003
    E os cadastros de Pais e Estado
    E acesso a página "/"
    Quando realizo o login com o usuário "100001" e senha "abcd"
    E a data do sistema for "10/03/2019"

  @do_document
  Cenário: Pré-Cadastro: Forma de Ingresso
    São definidas as formas como um aluno pode ingressar em um curso. Ação executada pelo perfil Administrador Acadêmico.

    Quando pesquiso por "Formas de Ingresso" e acesso o menu "Ensino::Cadastros Gerais::Formas de Ingresso"
    E clico no botão "Adicionar Forma de Ingresso"
    E preencho o formulário com os dados
      | Campo                    | Tipo     | Valor                                |
      | Descrição                | Texto    | Ampla Concorrência                   |
      | Ativo                    | Checkbox | marcar                               |
      | Classificação CENSUP     | Lista    | Enem                                 |
      | Classificação EDUCACENSO | Lista    | Exame de seleção sem reserva de vaga |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Pré-Cadastro: Convênio
    Dado acesso a página "/"
    Quando pesquiso por "Convênios" e acesso o menu "Ensino::Cadastros Gerais::Convênios"
    E clico no botão "Adicionar Convênio"
    Então vejo os seguintes campos no formulário
      | Campo     | Tipo  |
      | Descrição | Texto |
    Quando preencho o formulário com os dados
      | Campo     | Tipo  | Valor    |
      | Descrição | Texto | PRONATEC |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Pré-Cadastro: Cidade
    O cadastro de cidades é utilizado no ato de matrícula do aluno. Ação executada pelo perfil Administrador Acadêmico.

    Quando pesquiso por "Cidades" e acesso o menu "Ensino::Cadastros Gerais::Cidades"
    E clico no botão "Adicionar Cidade"
    E preencho o formulário com os dados
      | Campo | Tipo  | Valor |
      | Nome  | texto | Natal |
      | Estado  | lista | Rio Grande do Norte |
      | País | autocomplete | Brasil |
      | CEP Inicial | texto | 59000000 |
      | CEP Inicial | texto | 59149999 |
      | Código | texto | 2408102 |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  Cenário: Autenticar como Secretário Acadêmico
    Quando acesso o menu "Sair"
    Dado acesso a página "/"
    Quando realizo o login com o usuário "100002" e senha "abcd"

  @do_document
  Cenário: Efetuar Matrícula Institucional
    Cadastro realizado em 5 etapas coletando os dados aluno. Após finalização do cadastro pode ser impresso um PDF com o comprovante de inscrição. Ação executada pelo perfil Secretário Acadêmico.

    Dado os cadastros iniciais de raça
    Quando pesquiso por "Efetuar Matrícula Direta" e acesso o menu "Ensino::Procedimentos de Apoio::Efetuar Matrícula Direta"
    E preencho o formulário com os dados
      | Campo         | Tipo  | Valor          |
      | Nacionalidade | lista | Brasileira     |
      | CPF           | texto | 770.625.744-49 |
    E clico no botão "Continuar"
    E preencho o formulário com os dados
      | Campo              | Tipo         | Valor          |
      | Nome               | texto        | João da Silva  |
      | Sexo               | lista        | Masculino      |
      | Data de Nascimento | data         | 10/10/1990     |
      | Estado civil       | lista        | Solteiro       |
      | Nome da Mãe        | texto        | Maria da Silva |
      | Logradouro         | texto        | Rua abcd       |
      | Número             | texto        |            123 |
      | Bairro             | texto        | qwer           |
      | Cidade             | autocomplete | Natal          |
      | Zona Residencial   | lista        | Urbana         |
    E clico no botão "Continuar"
    E preencho o formulário com os dados
      | Campo                              | Tipo         | Valor                |
      | E-mail Pessoal                     | texto        | joao.silva@email.com |
      | Portador de Necessidades Especiais | lista        | Não                  |
      | Naturalidade                       | autocomplete | Natal                |
      | Raça                               | lista        | Parda                |
      | Nível de Ensino                    | lista        | Fundamental          |
      | Tipo da Instituição                | lista        | Pública              |
      | Ano de Conclusão                   | lista        |                 2018 |
    E clico no botão "Continuar"
    E preencho o formulário com os dados
      | Campo            | Tipo  | Valor      |
      | Tipo de Certidão | lista | Nascimento |
    E clico no botão "Continuar"
    E preencho o formulário com os dados
      | Campo             | Tipo         | Valor              |
      | Ano Letivo        | lista        |               2019 |
      | Período Letivo    | lista        |                  1 |
      | Turno             | lista        | Matutino           |
      | Forma de Ingresso | lista        | Ampla Concorrência |
      | Possui Convênio   | lista        | Sim                |
      | Convênio          | lista        | PRONATEC           |
      | Matriz/Curso      | autocomplete | Espec              |
    E clico no botão "Finalizar Matrícula Institucional"
    Então vejo mensagem de sucesso "Matrícula realizada com sucesso."

  @do_document
  Cenário: Matricular em Turma
    Cadastra o aluno matriculado no curso na turma criada para o curso. Ação executada pelo perfil Secretário Acadêmico.

    Quando pesquiso por "Turmas" e acesso o menu "Ensino::Turmas e Diários::Turmas"
    E olho a linha "Especialização"
    E clico no ícone de exibição
    E clico na aba "Alunos"
    E clico no botão "Adicionar Alunos"
    E seleciono o item "João da Silva" da lista
    E clico no botão "Matricular Alunos Selecionados"
    Então vejo mensagem de sucesso "Aluno(s) matriculado(s) com sucesso."
