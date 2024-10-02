# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro de um Estágio
  Essa funcionalidade cadastra um Estágio. No final
  desse teste o estado do estágio estará "Em Andamento".

  Cenário: Adicionando os usuários necessários para os testes Estágio
    Dado os seguintes usuários
      | Nome                             | Matrícula      | Setor    | Lotação  | Email           | CPF            | Senha | Grupo                            |
      | Coordenador de Estágio Sistêmico | 102001         | DIAC/CEN | DIAC/CEN | d01@ifrn.edu.br | 647.115.806-89 | abcd  | Coordenador de Estágio Sistêmico |
      | Coordenador de Estágio           | 102002         | DIAC/CEN | DIAC/CEN | d02@ifrn.edu.br | 735.785.191-54 | abcd  | Coordenador de Estágio           |
      | Professor Orientador 1           | 102003         | DIAC/CEN | DIAC/CEN | d03@ifrn.edu.br | 824.587.211-33 | abcd  | Professor                        |
      | Professor Orientador 2           | 102004         | DIAC/CEN | DIAC/CEN | d04@ifrn.edu.br | 948.852.240-20 | abcd  | Professor                        |
      | Aluno Estágio                    | 20191101011021 | DIAC/CEN | DIAC/CEN | aluno1@email.com | 440.337.400-07 | abcd | Aluno                            |
      | Representante Estágio            | 38325379618    | DIAC/CEN | DIAC/CEN | aluno2@email.com | 383.253.796-18 | abcd | Prestador de Serviço             |
    Dado os dados básicos para os estágios
    Quando a data do sistema for "10/01/2019"

  @do_document
  Cenário: O coordenador de estágio cria um novo estágio
    Dado acesso a página "/"
    Quando realizo o login com o usuário "102002" e senha "abcd"
    Então vejo o item de menu "Extensão::Estágio e Afins::Estágios"
    Quando acesso o menu "Extensão::Estágio e Afins::Estágios"
    Então vejo a página "Estágios"
    #E vejo mensagem de alerta "Nenhum Estágio encontrado."
    Quando clico no botão "Adicionar Estágio"
    Então vejo a página "Adicionar Estágio"
    E vejo os seguintes campos no formulário
      | Campo                   | Tipo         |
      | O estágio é obrigatório | Lista        |
      | Turno                   | Autocomplete |
      | Estagiário              | Autocomplete |
      | Concedente              | Autocomplete |
      | Representante da Concedente              | Autocomplete |
    E vejo o botão "Salvar"
    Quando clico no botão "Salvar"
    Então vejo mensagem de erro "Por favor, corrija os erros abaixo."
    E vejo os seguintes erros no formulário
      | Campo                   | Tipo         | Mensagem                 |
      | O estágio é obrigatório | Lista        |                          |
      | Turno                   | Autocomplete | Este campo é obrigatório |
      | Estagiário              | Autocomplete | Este campo é obrigatório |
      | Representante da Concedente              | Autocomplete | Este campo é obrigatório |

    Quando preencho o formulário com os dados
      | Campo                           | Tipo         | Valor                            |
      | O estágio é obrigatório         | Lista        | Estágio não-obrigatório          |
      | Turno                           | Autocomplete | Diurno                           |
      | Estagiário                      | Autocomplete | 20191101011021                   |
      | Concedente                      | Autocomplete | BANCO DO BRASIL SA               |
      | Representante da Concedente     | Autocomplete | Representante                    |
      | Professor Orientador            | Autocomplete | 102003                           |
      | Remunerada                      | Checkbox     | Marcar                           |
      | Tipo de Remuneração             | Autocomplete | Bolsa                            |
      | Bolsa (R$)                      | Texto        | 900,00                           |
      | Auxílio Transporte (R$)         | Texto        | 100,00                           |
      | Outros Benefícios (R$)          | Texto        | 100,00                           |
      | Descrição                       | TextArea     | Benfícios de vale refeição e etc |
      | Data de Início                  | Data         | 01/07/2018                       |
      | Data Prevista para Encerramento | Data         | 30/09/2018                       |
      | C.H. Semanal                    | Texto        | 20                               |
      | Plano de Atividades             | Arquivo      | imagem.png                       |
      | Termo de Compromisso            | Arquivo      | imagem.png                       |
      | Nome da Seguradora              | Texto        | Seguradora A                     |
      | Número da Apólice do Seguro     | Texto        | 10                               |
      | Supervisor                      | Autocomplete | Prestador 1                      |
      | Nome                            | Texto        | Supervisor                       |
      | Telefone                        | Texto        | 84999555555                      |
      | Cargo                           | Texto        | Supervisor de estagiário         |
      | E-mail                          | Texto        | supervisor@email.com             |
      | Observação                      | TextArea     | Entrar em contato por e-mail     |

    Quando clico no link "Adicionar outro(a) Atividade do Estágio"
    Quando clico no link "Adicionar outro(a) Atividade do Estágio"
    Quando preencho o inline "Relação de Atividades do Estágio" com os dados
      | Texto       | Checkbox  |
      | Atividade 1 | Desmarcar |
      | Atividade 2 | Desmarcar |
      | Atividade 3 | Desmarcar |

    Quando clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."
    Quando acesso o menu "Sair"


  Cenário: Verifica a visualização do estágio pelo Sistemico
    Dado a atual página
    Quando realizo o login com o usuário "102001" e senha "abcd"
    Então vejo o item de menu "Extensão::Estágio e Afins::Estágios"
    Quando acesso o menu "Extensão::Estágio e Afins::Estágios"
    Então vejo a página "Estágios"
    #E nao vejo mensagem de alerta "Nenhum Estágio encontrado."
    Quando acesso o menu "Sair"

  @do_document
  Cenário: O coordenador de Executa Notificações de Pendências de Todos os Estágios
    Dado a atual página
    Quando realizo o login com o usuário "102002" e senha "abcd"
    Então vejo o item de menu "Extensão::Estágio e Afins::Estágios"
    Quando acesso o menu "Extensão::Estágio e Afins::Estágios"
    Então vejo a página "Estágios"
    Quando clico no botão "Enviar Notificações de Pendências"
    Então vejo mensagem de sucesso "Foram enviados e-mails referentes aos estágios com pendências."

  @do_document
  Cenário: O coordenador de Executa Notificação de Pendências de um Estágio em Particular
    Quando acesso o menu "Extensão::Estágio e Afins::Estágios"
    Então vejo a página "Estágios"
    Quando olho para a listagem
    E olho a linha "Aluno"
    E clico no ícone de exibição
    Então vejo a página "Estágio de Aluno Estágio (20191101011021) em BANCO DO BRASIL SA (00.000.000/0001-91)"
    Quando clico na aba "Notificações"
    Quando clico no botão "Notificar Pendências"
    Então vejo mensagem de sucesso "Foram enviadas as notificações."


  @do_document
  Cenário: O coordenador Adiciona Aditivo Contratual
    Quando acesso o menu "Extensão::Estágio e Afins::Estágios"
    Então vejo a página "Estágios"
    Quando olho para a listagem
    E olho a linha "Aluno"
    Quando clico no ícone de exibição
    Então vejo a página "Estágio de Aluno Estágio (20191101011021) em BANCO DO BRASIL SA (00.000.000/0001-91)"
    Quando clico na aba "Documentação e Aditivos"
    Então vejo o botão "Adicionar Aditivo"
    Quando clico no botão "Adicionar Aditivo"
    Quando preencho o formulário com os dados
      | Campo                           | Tipo              | Valor                                           |
      | Tipos de Aditivo Contratual     | checkbox multiplo | Professor Orientador, Tempo                     |
      | Início da Vigência              | Data              | 20/07/2018                                      |
      | Aditivo                         | Arquivo           | imagem.png                                      |
      | Descrição                       | Texto             | Adição de novo professor orientador e de tempo. |
      | Orientador                      | autocomplete      | 102004                                          |
      | Data Prevista para Encerramento | Data              | 30/09/2018                                      |
    Quando clico no botão "Salvar"
    Então vejo mensagem de sucesso "Aditivo adicionado com sucesso."
    Quando acesso o menu "Sair"
