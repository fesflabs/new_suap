# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Cadastros

  Cenário: Adicionando os usuários necessários para os testes AE
    Dado os seguintes usuários
      | Nome               | Matrícula      | Setor | Lotação | Email                         | CPF            | Senha | Grupo                                          |
      | Coord_AE Sistemico | 103001         | CZN   | CZN     | coordaesistemico@ifrn.edu.br  | 645.433.195-40 | abcd  | Coordenador de Atividades Estudantis Sistêmico |
      | Assistente Social  | 103002         | CZN   | CZN     | assistente_social@ifrn.edu.br | 188.135.291-98 | abcd  | Assistente Social                              |
      | Aluno AE           | 20191101011031 | CZN   | CZN     | aluno_ae@ifrn.edu.br          | 188.135.291-98 | abcd  | Aluno                                          |

  @do_document
  Cenário: Tipo de Programa
  De acordo com o Tipo do Programa, cada Programa terá informações específicas sendo solicitadas nos formulários de inscrição e participação dos alunos.
  Ação executada pelo Coordenador de Atividades Estudantis Sistêmico.

    Dado acesso a página "/"
    Quando a data do sistema for "01/11/2019"
    Quando realizo o login com o usuário "103001" e senha "abcd"
    E acesso o menu "Atividades Estudantis::Cadastros::Tipos de Programas"
    Então vejo a página "Tipos de Programa"
    E vejo o botão "Adicionar Tipo de Programa"
    Quando clico no botão "Adicionar Tipo de Programa"
    Então vejo a página "Adicionar Tipo de Programa"
    E vejo os seguintes campos no formulário
      | Campo     | Tipo     |
      | Título    | Texto    |
      | Descrição | TextArea |
      | Ativo     | checkbox |
    E vejo o botão "Salvar"
    Quando preencho o formulário com os dados
      | Campo     | Tipo     | Valor                          |
      | Título    | Texto    | Alimentação Estudantil         |
      | Descrição | TextArea | descrição do tipo do  programa |
      | Ativo     | checkbox | marcar                         |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Programa
  No cadastro do Programa é possível definir o nome, o tipo, a qual campus o programa está vinculado e quais os tipos de atendimentos vinculados ao Programa.
  Também é possível informar se os alunos poderão solicitar o benefício diretamente pelo SUAP, como, por exemplo, requerer o agendamento de refeição, além de informar o público-alvo, que pode incluir alunos de outros campi.
  Ação executada pelo Coordenador de Atividades Estudantis Sistêmico.

    Quando acesso o menu "Atividades Estudantis::Serviço Social::Programas::Programas"
    Então vejo a página "Programas"
    E vejo o botão "Adicionar Programa"
    Quando clico no botão "Adicionar Programa"
    Então vejo a página "Adicionar Programa"
    E vejo os seguintes campos no formulário
      | Campo                                | Tipo                   |
      | Tipo de Programa                     | Autocomplete           |
      | Descrição                            | TextArea               |
      | Campus                               | Autocomplete           |
      | Atendimentos incluídos               | FilteredSelectMultiple |
      | Impedir que aluno solicite benefício | checkbox               |
      | Público-Alvo                         | FilteredSelectMultiple |
    E vejo o botão "Salvar"
    Quando preencho o formulário com os dados
      | Campo                                | Tipo                   | Valor                  |
      | Tipo de Programa                     | Autocomplete           | Alimentação Estudantil |
      | Descrição                            | TextArea               | descrição do programa  |
      | Campus                               | Autocomplete           | CZN                    |
      | Impedir que aluno solicite benefício | checkbox               | marcar                 |
      | Público-Alvo                         | FilteredSelectMultiple | CZN                    |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

  @do_document
  Cenário: Edital do Programa
  O cadastro do edital define os tipos de programas que receberão novos participantes.
  Ação executada pelo Coordenador de Atividades Estudantis Sistêmico.

    Quando acesso o menu "Atividades Estudantis::Serviço Social::Programas::Editais"
    Então vejo a página "Editais da Assistência Estudantil"
    E vejo o botão "Adicionar Edital da Assistência Estudantil"
    Quando clico no botão "Adicionar Edital da Assistência Estudantil"
    Então vejo a página "Adicionar Edital da Assistência Estudantil"
    E vejo os seguintes campos no formulário
      | Campo              | Tipo                  |
      | Descrição          | TextArea              |
      | Tipos de Programa  | Autocomplete multiplo |
      | Link para o Edital | Texto                 |

    E vejo o botão "Salvar"
    Quando preencho o formulário com os dados
      | Campo              | Tipo                  | Valor                                      |
      | Descrição          | TextArea              | Edital 001/2018 do Programa de Alimentação |
      | Tipos de Programa  | Autocomplete multiplo | Alimentação Estudantil                     |
      | Link para o Edital | Texto                 | http://portal.ifrn.edu.br/link_edital.pdf  |

    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."
    Quando acesso o menu "Sair"


  @do_document
  Cenário: Ofertas de Alimentação
  O cadastro de Ofertas de Alimentação está ligado exclusivamente aos programas do tipo 'Alimentação Estudantil' e serve para o controle diário de refeições. O cadastro é feito semanalmente.
  De acordo com a oferta diária para cada refeição, os gestores controlam a demanda, levando em conta a quantidade de participantes do programa de alimentação, dos agendamentos cadastrados e dos registros avulsos.
  Ação executada pelo Assistente Social ou pelo Coordenador de Atividades Estudantis.
    Dado acesso a página "/"
    Quando realizo o login com o usuário "103002" e senha "abcd"
    E a data do sistema for "01/11/2019"
    E acesso o menu "Atividades Estudantis::Serviço Social::Programas::Ofertas::Refeições"
    Então vejo a página "Ofertas de Refeições"
    E vejo o botão "Adicionar Oferta de Refeições"
    Quando clico no botão "Adicionar Oferta de Refeições"
    Então vejo a página "Adicionar Oferta de Refeições"
    E vejo os seguintes campos no formulário
      | Campo                             | Tipo  |
      | Campus                            | Lista |
      | Segunda-feira do Início da Oferta | Data  |
      | Sexta-feira do Término da Oferta  | Data  |


    E vejo o botão "Salvar"
    Quando preencho o formulário com os dados
      | Campo                             | Tipo         | Valor      |
      | Campus                            | Autocomplete | CZN        |
      | Segunda-feira do Início da Oferta | Data         | 05/03/2018 |
      | Sexta-feira do Término da Oferta  | Data         | 09/03/2018 |
      | Almoço/Segunda                    | Texto        | 100        |
      | Almoço/Terça                      | Texto        | 100        |
      | Almoço/Quarta                     | Texto        | 100        |
      | Almoço/Quinta                     | Texto        | 100        |
      | Almoço/Sexta                      | Texto        | 100        |

    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


  @do_document
  Cenário: Período de Inscrição
  Para cada edital cadastrado, um ou mais períodos de inscrição podem ser criados. Um período de inscrição é vinculado à um campus e define quais programas estarão com inscrições abertas.
  Após o cadastro de um período de inscrição, os alunos pertencentes aos campi público-alvo dos programas informados poderão se inscrever nos mesmos através de um alerta exibido na tela inicial do SUAP.
  Ação executada pelo Assistente Social ou pelo Coordenador de Atividades Estudantis.
    Quando acesso o menu "Atividades Estudantis::Serviço Social::Programas::Períodos de Inscrição"
    Então vejo a página "Períodos de Inscrição"
    E vejo o botão "Adicionar Período de Inscrição"
    Quando clico no botão "Adicionar Período de Inscrição"
    Então vejo a página "Adicionar Período de Inscrição"
    E vejo os seguintes campos no formulário
      | Campo                          | Tipo                  |
      | Edital                         | Autocomplete          |
      | Campus                         | Autocomplete          |
      | Programas Vinculados           | Autocomplete multiplo |
      | Data de Início das Inscrições  | Data                  |
      | Data de Término das Inscrições | Data                  |

    E vejo o botão "Salvar"
    Quando preencho o formulário com os dados
      | Campo                          | Tipo                  | Valor                                      |
      | Edital                         | Autocomplete          | Edital 001/2018 do Programa de Alimentação |
      | Campus                         | Autocomplete          | CZN                                        |
      | Programas Vinculados           | Autocomplete multiplo | Alimentação Estudantil (CZN)               |
      | Data de Início das Inscrições  | Data                  | 01/01/2019                                 |
      | Data de Término das Inscrições | Data                  | 31/03/2020                                 |

    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."
    Quando acesso o menu "Sair"


  Cenário: Adicionando os Dados básicos para os testes AE
    Dado os dados basicos cadastrados do ae
