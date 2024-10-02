# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Cadastro de uma Aprendizagem
    Essa funcionalidade cadastra uma Aprendizagem. No final
    desse teste o estado da estará "Em Andamento".

  @do_document
  Cenário: O coordenador de estágio cria uma nova aprendizagem
    Dado acesso a página "/"
    Quando realizo o login com o usuário "102002" e senha "abcd"
    E acesso o menu "Extensão::Estágio e Afins::Aprendizagens"
    Então vejo a página "Aprendizagens"
    #E vejo mensagem de alerta "Nenhum Aprendizagem encontrado."
    Quando clico no botão "Adicionar Aprendizagem"
    Então vejo a página "Adicionar Aprendizagem"
    E vejo os seguintes campos no formulário
      | Campo      | Tipo         |
      | Aprendiz   | Autocomplete |
      | Convênio   | Autocomplete |
      | Turno      | Autocomplete |
      | Concedente | Autocomplete |
      | Orientador | Autocomplete |
    E vejo o botão "Salvar"
    Quando clico no botão "Salvar"
    Então vejo mensagem de erro "Por favor, corrija os erros abaixo."
    E vejo os seguintes erros no formulário
      | Campo      | Tipo         | Mensagem                 |
      | Aprendiz   | Autocomplete | Este campo é obrigatório |
      | Convênio   | Autocomplete |                          |
      | Turno      | Autocomplete | Este campo é obrigatório |
      | Concedente | Autocomplete | Este campo é obrigatório |
      | Orientador | Autocomplete | Este campo é obrigatório |
    Quando preencho o formulário com os dados
      | Campo                                                                             | Tipo         | Valor                         |
      | Aprendiz                                                                          | Autocomplete |                20191101011021 |
      | Turno                                                                             | Autocomplete | Diurno                        |
      | Concedente                                                                        | Autocomplete | BANCO DO BRASIL SA            |
      | Orientador                                                                        | Autocomplete |                        102004 |
      | Unidade da Federação                                                              | Lista        | Estado                        |
      | Município                                                                         | Autocomplete | Cidade                        |
      | Logradouro                                                                        | Texto        | Av. Prudente de Morais        |
      | Nº                                                                                | Texto        |                          0800 |
      | Complemento                                                                       | Texto        |                               |
      | Bairro                                                                            | Texto        | Tirol                         |
      | CEP                                                                               | Texto        | 59.000-000                    |
      | Senhor Coordenador de Estágio favor confirmar que esta aprendizagem é remunerada. | Checkbox     | Marcar                        |
      | Auxílio Transporte (R$)                                                           | Texto        |                           200 |
      | Outros Benefícios (R$)                                                            | Texto        |                           100 |
      | Descrição dos Outros Benefícios                                                   | Textarea     | auxílio cantina               |
      | Contrato de Aprendizagem                                                          | Arquivo      | contrato.pdf                  |
      | Anotação na Carteira de Trabalho                                                  | Arquivo      | anotacao_ctps.pdf             |
      | Resumo do Curso de Aprendizagem                                                   | Arquivo      | resumo_curso_aprendizagem.pdf |
      | Nome                                                                              | Texto        | Nome Supervisor               |
      | Cargo                                                                             | Texto        | Supervisor de estagiário      |
      | E-mail                                                                            | Texto        | supervisor@email.com          |
      | Observação                                                                        | TextArea     | Entrar em contato por e-mail  |
      | O aluno fará o módulo I?                                                          | Checkbox     | Marcar                        |
    Então vejo os seguintes campos no formulário
      | Campo                              | Tipo     |
      | Descrição das Atividades do Módulo | Textarea |
    Quando preencho o formulário com os dados
      | Campo                              | Tipo     | Valor              |
      | Descrição das Atividades do Módulo | Textarea | Atividade 1, 2, 3. |
      | Data de Início do Módulo           | Data     | 01/01/2018         |
      | Data de Fim do Módulo              | Data     | 31/12/2018         |
      | Carga Horária Teórica Semanal      | Texto    |                 10 |
      | Carga Horária Prática Semanal      | Texto    |                 20 |
    Quando olho e clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."
    Quando acesso o menu "Sair"

  Esquema do Cenário: Verifica a visualização da aprendizagem pelo <Papel>
    Dado acesso a página "/"
    Quando realizo o login com o usuário "<Papel>" e senha "abcd"
    E acesso o menu "Extensão::Estágio e Afins::Aprendizagens"
    Então vejo a página "Aprendizagens"
    #E nao vejo mensagem de alerta "Nenhum Aprendizagem encontrado."
    Quando acesso o menu "Sair"

    Exemplos:
      | Papel  |
      | 102001 |
      | 102002 |

  @do_document
  Cenário: O coordenador de estágio Executa Notificações de Pendências de Todas as Aprendizagens
    Dado acesso a página "/"
    Quando realizo o login com o usuário "102002" e senha "abcd"
    E acesso o menu "Extensão::Estágio e Afins::Aprendizagens"
    Então vejo a página "Aprendizagens"
    Quando clico no botão "Enviar Notificações de Pendências"
    Então vejo mensagem de sucesso "Foram enviados e-mails referentes às aprendizagens com pendências."
    Quando acesso o menu "Sair"

  @do_document
  Cenário: O coordenador de estágio cadastra um aditivo contratual
    Dado acesso a página "/"
    Quando realizo o login com o usuário "102002" e senha "abcd"
    E acesso o menu "Extensão::Estágio e Afins::Aprendizagens"
    E olho para a listagem
    E olho a linha "Aluno"
    Quando clico no ícone de exibição
    Então vejo a página "Aprendizagem do aluno Aluno Estágio (20191101011021) na concedente Banco do Brasil (00000000000191)"
    Quando clico na aba "Documentação e Aditivos"
    Quando clico no botão "Cadastrar Aditivo"
    Quando preencho o formulário com os dados
      | Campo                       | Tipo              | Valor                                                       |
      | Tipos de Aditivo Contratual | Checkbox Multiplo | Professor Orientador, Horário                               |
      | Início da Vigência          | Data              | 15/02/2018                                                  |
      | Aditivo                     | Arquivo           | imagem.png                                                  |
      | Descrição                   | Textarea          | Adição de novo professor orientador e alteração de horário. |
      | Orientador                  | Autocomplete      |                                                      102003 |
      | Turno                       | Lista             | Noturno                                                     |
    Quando clico no botão "Salvar"
    Então vejo mensagem de sucesso "Aditivo adicionado com sucesso."
    Quando acesso o menu "Sair"
