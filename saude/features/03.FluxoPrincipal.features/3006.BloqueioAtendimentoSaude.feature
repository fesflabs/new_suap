# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Listagem de Pacientes Bloqueados
  Exibe a lista de pacientes impossibilitados de agendar horário de atendimento

  Cenário: Adiciona os usuarios necessarios para essa funcionalidade
    Dado os usuarios do SAUDE
    E  os seguintes usuários
      | Nome        | Matrícula      | Setor | Lotação | Email              | CPF            | Senha | Grupo |
      | Aluno Teste | 20191101011111 | CZN   | CZN     | aluno1@ifrn.edu.br | 559.454.350-31 | abcd  | Aluno |
    E os seguintes campi
    E os seguintes pacientes bloqueados
    Quando acesso a página "/"
    E realizo o login com o usuário "111001" e senha "abcd"


  @do_document
  Cenário: Buscar Pacientes Bloqueados
  Listar e buscar pacientes bloqueados.
    Dado acesso a página "/"
    Quando acesso o menu "Saúde::Relatórios::Listagem de Pacientes Bloqueados"
    E preencho o formulário com os dados
      | Campo  | Tipo  | Valor |
      | Campus | Lista | CZN   |
      | Ano    | Lista | 2019  |
    Então vejo mais de 0 resultados na tabela


  Cenário: Encerrando a feature
    Dado acesso a página "/"
    Quando acesso o menu "Sair"