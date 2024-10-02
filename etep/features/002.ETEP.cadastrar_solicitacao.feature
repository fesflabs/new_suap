# -*- coding: utf-8 -*-
# language: pt
Funcionalidade: Cadastrar Solicitação de Acompanhamento

  @do_document
  Cenário: Cadastrar Solicitação de Acompanhamento
    Ação executada pelo membro do grupo Secretário Acadêmico.

    Dado acesso a página "/"
    Quando realizo o login com o usuário "111125" e senha "abcd"
    E acesso o menu "Ensino::ETEP::Adicionar Solicitação"
    Então vejo a página "Adicionar Solicitação de Acompanhamento"
    E vejo os seguintes campos no formulário
      | Campo     | Tipo                   |
      | Aluno     | Autocomplete           |
      | Descrição | Textarea               |
      | Tipos     | FilteredSelectMultiple |
    E vejo o botão "Salvar"
    Quando preencho o formulário com os dados
      | Campo     | Tipo                   | Valor                                      |
      | Aluno     | Autocomplete           | Aluno Etep                                 |
      | Descrição | Textarea               | Descrição da necessidade de acompanhamento |
      | Tipos     | FilteredSelectMultiple | Aprendizagem                               |
    E clico no botão "Salvar"
