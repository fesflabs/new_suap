# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Abertura de uma demanda
    Essa funcionalidade verifica a criação de uma nova demanda e o acesso dos participantes nesse processo. No final
    desse teste a demanda passará do estado "Aberta" para "Em negociação"

  Cenário: Adicionando os usuários necessários para os testes demandas
    Dado os seguintes usuários
      | Nome            | Matrícula | Setor    | Lotação  | Email           | CPF            | Senha | Grupo         |
      | Demandante      |    105001 | DIAC/CEN | DIAC/CEN | d01@ifrn.edu.br | 647.115.806-89 | abcd  | Demandante    |
      | Analista do Demandas |    105002 | DIAC/CZN | DIAC/CZN | d02@ifrn.edu.br | 735.785.191-54 | abcd  | Analista      |
      | Desenvolvedor   |    105003 | DIAC/CZN | DIAC/CZN | d03@ifrn.edu.br | 824.587.211-33 | abcd  | Desenvolvedor |
      | Servidor Comum  |    105004 | DIAC/CZN | DIAC/CZN | d04@ifrn.edu.br | 977.236.780-70 | abcd  | Servidor      |
      | Servidor Comum2 |    105005 | DIAC/CZN | DIAC/CZN | d05@ifrn.edu.br | 061.292.320-71 | abcd  | Servidor      |
    Dado os cadastros básicos do módulo de demandas

  @do_document
  Cenário: O demandante cria uma nova demanda
    Dado acesso a página "/"
    Quando realizo o login com o usuário "105001" e senha "abcd"
    E acesso o menu "Tec. da Informação::Desenvolvimento::Demandas"
    Então vejo a página "Demandas"
    Quando clico no botão "Visualizar Todas"
    Então vejo a página "Demandas"
    E vejo mensagem de alerta "Nenhum Demanda encontrado."
    Quando clico no botão "Adicionar Demanda"
    Então vejo a página "Adicionar Demanda"
    E vejo os seguintes campos no formulário
      | Campo                | Tipo                  |
      | Área de Atuação      | Autocomplete          |
      | Título da Demanda    | Texto                 |
      | Descrição da Demanda | TextArea              |
      | Demandantes          | Autocomplete Multiplo |
      | Interessados         | Autocomplete Multiplo |
    E vejo o botão "Salvar"
    Quando clico no botão "Salvar"
    Então vejo mensagem de erro "Por favor, corrija os erros abaixo."
    E vejo os seguintes erros no formulário
      | Campo                | Tipo         | Mensagem                 |
      | Área de Atuação      | Autocomplete | Este campo é obrigatório |
      | Título da Demanda    | Texto        | Este campo é obrigatório |
      | Descrição da Demanda | TextArea     | Este campo é obrigatório |
    Quando preencho o formulário com os dados
      | Campo                | Tipo         | Valor                    |
      | Área de Atuação      | Autocomplete | Tecnologia da Informação |
      | Título da Demanda    | Texto        | Demanda 1                |
      | Descrição da Demanda | TextArea     | Primeira demanda         |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."
    E nao vejo mensagem de alerta "Nenhum Demanda encontrado."
    Quando acesso o menu "Sair"

  Esquema do Cenário: Verifica a visualização da demanda pelo <Papel>
    Dado acesso a página "/"
    Quando realizo o login com o usuário "<Papel>" e senha "abcd"
    E acesso o menu "Tec. da Informação::Desenvolvimento::Demandas"
    Então vejo a página "Demandas"
    Quando clico no botão "Visualizar Todas"
    Então vejo a página "Demandas"
    E nao vejo mensagem de alerta "Nenhum Demanda encontrado."
    Quando acesso o menu "Sair"

    Exemplos:
      | Papel  |
      | 105003 |
      | 105002 |

  @do_document
  Cenário: Adiciona o analista e desenvolvedor para a demanda criada
    Dado acesso a página "/"
    Quando realizo o login com o usuário "105002" e senha "abcd"
    E acesso o menu "Tec. da Informação::Desenvolvimento::Demandas"
    Então vejo a página "Demandas"
    Quando clico no botão "Visualizar Todas"
    Então vejo a página "Demandas"
    Quando olho a linha "Demanda 1"
    Então vejo o texto "Demandante"
    Quando clico no ícone de edição
    Então vejo a página "Editar Demanda 1: Demanda 1"
    E vejo os seguintes campos no formulário
      | Campo                              | Tipo                  |
      | Título da Demanda                  | Texto                 |
      | Descrição da Demanda               | TextArea              |
      | Demandantes                        | Autocomplete Multiplo |
      | Interessados                       | Autocomplete Multiplo |
      | Analistas                          | Autocomplete Multiplo |
      | Desenvolvedores                    | Autocomplete Multiplo |
      | Tags                               | Autocomplete Multiplo |
      | ID do Repositório GIT              | Texto                 |
      | URL para Ambiente de Homologação   | Texto                 |
      | Senha para Ambiente de Homologação | Texto                 |
    Quando preencho o formulário com os dados
      | Campo           | Tipo                  | Valor  |
      | Analistas       | Autocomplete Multiplo | 105002 |
      | Desenvolvedores | Autocomplete Multiplo | 105003 |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Atualização realizada com sucesso."
    Quando olho para a listagem
    E olho a linha "Demanda 1"
    Então vejo o texto "Demandante"
    E vejo o texto "Analista"
    E vejo o texto "Desenvolvedor"
    Quando acesso o menu "Sair"

  @do_document
  Cenário: Verifica se o demandante tem acesso a atualização de situação
    Dado acesso a página "/"
    Quando realizo o login com o usuário "105001" e senha "abcd"
    E acesso o menu "Tec. da Informação::Desenvolvimento::Demandas"
    Quando clico no botão "Visualizar Todas"
    Então vejo a página "Demandas"
    Quando olho para a listagem
    E olho a linha "Demanda 1"
    E clico no ícone de exibição
    Então vejo a página "Demanda 1: Demanda 1"
    E nao vejo o botão "Alterar Etapa"
    Quando acesso o menu "Sair"

  @do_document
  Cenário: Verifica se o desenvolvedor tem acesso a atualização de situação
    Dado acesso a página "/"
    Quando realizo o login com o usuário "105003" e senha "abcd"
    Quando acesso o menu "Tec. da Informação::Desenvolvimento::Demandas"
    Então vejo a página "Demandas"
    Quando clico no botão "Visualizar Todas"
    Então vejo a página "Demandas"
    Quando olho para a listagem
    E olho a linha "Demanda 1"
    E clico no ícone de exibição
    Então vejo a página "Demanda 1: Demanda 1"
    E vejo o botão "Alterar Etapa"
    Quando acesso o menu "Sair"

  @do_document
  Cenário: Muda a situação da demanda para Em negociação
    Dado acesso a página "/"
    Quando realizo o login com o usuário "105002" e senha "abcd"
    E acesso o menu "Tec. da Informação::Desenvolvimento::Demandas"
    Então vejo a página "Demandas"
    Quando clico no botão "Visualizar Todas"
    Então vejo a página "Demandas"
    Quando olho para a listagem
    E olho a linha "Demanda 1"
    Quando clico no ícone de exibição
    Então vejo a página "Demanda 1: Demanda 1"
    Quando clico no botão "Alterar Etapa"
    E clico no botão "Negociar"
    E clico no botão "Enviar"
    Então vejo mensagem de sucesso "A etapa da demanda foi alterada."
    E vejo o status "Em negociação"
