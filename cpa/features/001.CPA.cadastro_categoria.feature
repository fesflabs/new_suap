# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Cadastro de Categoria de Questionário

  Cenário: Adicionando os usuários necessários para os testes CPA
    Dado os seguintes usuários
      | Nome            | Matrícula | Setor | Lotação | Email                            | CPF            | Senha | Grupo            |
      | Gerente CPA     |    802021 | CZN   | CZN     | gerente_cpa@ifrn.edu.br          | 838.771.730-47 | abcd  | cpa_gerente      |
      | Visualizar CPA  |    802022 | CZN   | CZN     | visualizador_cpa@ifrn.edu.br     | 975.215.430-17 | abcd  | cpa_visualizador |
      | Respondente CPA |    802023 | CZN   | CZN     | servidor_respondente@ifrn.edu.br | 950.147.300-78 | abcd  | Servidor         |

  @do_document
  Cenário: Cadastro de Categoria de Questionário
    Cadastro de Categoria de Questionário.
    Ação executada por um membro do grupo cpa_gerente.

    Dado acesso a página "/"
    Quando realizo o login com o usuário "802021" e senha "abcd"
    E acesso o menu "Des. Institucional::Auto-Avaliação::Categorias"
    Então vejo a página "Categorias"
    E vejo o botão "Adicionar Categoria"
    Quando clico no botão "Adicionar Categoria"
    Então vejo a página "Adicionar Categoria"
    E vejo os seguintes campos no formulário
      | Campo | Tipo  |
      | Nome  | Texto |
    E vejo o botão "Salvar"
    Quando preencho o formulário com os dados
      | Campo | Tipo  | Valor                                                       |
      | Nome  | Texto | ORGANIZAÇÃO, GESTÃO, PLANEJAMENTO E AVALIAÇÃO INSTITUCIONAL |
    E clico no botão "Salvar"
    Então vejo mensagem de sucesso "Cadastro realizado com sucesso."
