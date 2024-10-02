# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Fluxo para a Publicação da Obra

	@do_document
	Cenário: Verificação Antiplágio
		Dado acesso a página "/"
        Quando realizo o login com o usuário "108007" e senha "abcd"
		E a data do sistema for "13/01/2018"
		E acesso o menu "Pesquisa::Editora::Submissão de Obras::Obras Submetidas"
		Então vejo a página "Obras"
		Quando olho a linha "título da obra"
		E clico no ícone de exibição
        Então vejo a página "Visualizar Obra: título da obra"
        Quando clico na aba "Verificação Antiplágio"
		Então vejo os seguintes campos no formulário
			| Campo                                                      | Tipo     |
			| Autêntica                                                  | Lista    |
			| Observações                                                | TextArea |
		E vejo o botão "Salvar"
        Quando preencho o formulário com os dados
			| Campo                                                      | Tipo     | Valor                 |
			| Autêntica                                                  | Lista    | Sim                 |
		E clico no botão "Salvar"
        Então vejo mensagem de sucesso "Verificação de autenticidade realizada com sucesso."
        
	@do_document
	Cenário: Análise Preliminar
		Dado acesso a página "/"
		Quando a data do sistema for "27/01/2018"
		Quando acesso o menu "Pesquisa::Editora::Submissão de Obras::Obras Submetidas"
		Então vejo a página "Obras"
		Quando olho a linha "título da obra"
		E clico no ícone de exibição
        Então vejo a página "Visualizar Obra: título da obra"
        Quando clico na aba "Análise Preliminar"
		Então vejo os seguintes campos no formulário
			| Campo                                                      | Tipo     |
			| Situação da Obra                                           | Lista    |
		E vejo o botão "Salvar"
        Quando preencho o formulário com os dados
			| Campo                                                      | Tipo     | Valor                 |
			| Situação da Obra                                           | Lista    | Habilitada            |
		E clico no botão "Salvar"
        Então vejo mensagem de sucesso "Avaliação da editora realizada com sucesso."
	
	@do_document
	Cenário: Indicação do Conselheiro
		Dado acesso a página "/"
		Quando acesso o menu "Pesquisa::Editora::Submissão de Obras::Obras Submetidas"
		Então vejo a página "Obras"
		Quando olho a linha "título da obra"
		E clico no ícone de exibição
        Então vejo a página "Visualizar Obra: título da obra"
		Quando clico na aba "Conselho Editorial"
		Então vejo o botão "Indicar Conselheiro"
		Quando clico no botão "Indicar Conselheiro"
		Então vejo a página "Indicar Conselheiro"
		E vejo os seguintes campos no formulário
			| Campo                                                      | Tipo     |
			| Usuário                                                    | Autocomplete Multiplo    |
		E vejo o botão "Enviar"
        Quando preencho o formulário com os dados
			| Campo                                                      | Tipo     | Valor                 |
			| Usuário                                                    | Autocomplete Multiplo   | Conselheiro Editora            |
		E clico no botão "Enviar"
        Então vejo mensagem de sucesso "Conselheiro indicado com sucesso."

	Cenário: Sai do sistema
		Quando acesso o menu "Sair"

	@do_document
	Cenário: Indicação do Parecerista
		Dado acesso a página "/"
        Quando realizo o login com o usuário "108008" e senha "abcd"
		E acesso o menu "Pesquisa::Editora::Submissão de Obras::Obras Submetidas"
		Então vejo a página "Obras"
		Quando olho a linha "título da obra"
		E clico no ícone de exibição
        Então vejo a página "Visualizar Obra: título da obra"
		Quando clico na aba "Análise de Parecerista"
		Então vejo o botão "Indicar Parecerista"
		Quando clico no botão "Indicar Parecerista"
		Então vejo a página "Indicar Parecerista"
		E vejo os seguintes campos no formulário
			| Campo                                                      | Tipo     |
			| Usuário                                                    | Autocomplete Multiplo    |
		E vejo o botão "Enviar"
        Quando preencho o formulário com os dados
			| Campo                                                      | Tipo     | Valor                 |
			| Usuário                                                    | Autocomplete Multiplo   | Parecerista Obra            |
		E clico no botão "Enviar"
        Então vejo mensagem de sucesso "Parecerista indicado com sucesso."

	Cenário: Sai do sistema
		Quando acesso o menu "Sair"

	@do_document
	Cenário: Cadastro da Área de Conhecimento do Parecerista
		Dado acesso a página "/"
    	Quando realizo o login com o usuário "34245605880" e senha "abcd"
		E acesso o menu "Pesquisa::Editora::Áreas de Conhecimento de Interesse"
		Então vejo a página "Cadastrar Áreas de Conhecimento do seu Interesse"
		Quando preencho o formulário com os dados
			| Campo                 | Tipo              | Valor               |
			| Áreas de Conhecimento | checkbox popup | MATEMÁTICA (CIÊNCIAS EXATAS E DA TERRA) |
		E clico no botão "Salvar"
        Então vejo mensagem de sucesso "Áreas de conhecimento cadastradas com sucesso."
      
	@do_document
	Cenário: Avaliação da Obra
		Dado acesso a página "/"
		Quando acesso o menu "Pesquisa::Editora::Submissão de Obras::Obras Submetidas"
		Então vejo a página "Obras"
		Quando olho a linha "título da obra"
		E clico no ícone de exibição
        Então vejo a página "Visualizar Obra: título da obra"
		Quando clico na aba "Análise de Parecerista"
		Então vejo o botão "Avaliar Obra"
		Quando clico no botão "Avaliar Obra"
		Então vejo a página "Avaliar Obra"
		E vejo os seguintes campos no formulário
			| Campo                                                      | Tipo       |
			| Avaliação                                                  | Lista      |
			| Nota                                                       | Lista      |
			| Observações Complementares                                 | TextArea   |
			| Parecer                                                    | Arquivo    |
		E vejo o botão "Salvar"
        Quando preencho o formulário com os dados
			| Campo                                                      | Tipo       | Valor               |
			| Avaliação                                                  | Lista      | Aprovada            |
			| Nota                                                       | Lista      | 10.0                |
			| Observações Complementares                                 | Texto rico   | observações         |
			| Parecer                                                    | Arquivo    | parecer.png         |
		E clico no botão "Salvar"
        Então vejo mensagem de sucesso "Parecer salvo com sucesso."

      Cenário: Sai do sistema
        Quando acesso o menu "Sair"

	@do_document
	Cenário: Emissão do Parecer
		Dado acesso a página "/"
        Quando realizo o login com o usuário "108008" e senha "abcd"
		E acesso o menu "Pesquisa::Editora::Submissão de Obras::Obras Submetidas"
		Então vejo a página "Obras"
		Quando olho a linha "título da obra"
		E clico no ícone de exibição
        Então vejo a página "Visualizar Obra: título da obra"
		Quando clico na aba "Conselho Editorial"
		Então vejo o botão "Emitir Parecer"
		Quando clico no botão "Emitir Parecer"
		Então vejo a página "Emitir Parecer"
		E vejo os seguintes campos no formulário
			| Campo                                                      | Tipo        |
			| Parecer                                                    | Lista       |
			| Observações                                                | TextArea    |
		E vejo o botão "Salvar"
        Quando preencho o formulário com os dados
			| Campo                                                      | Tipo     | Valor                 |
			| Parecer                                                    | Lista    | Favorável             |
			| Observações                                                | Texto rico  | observações do conselheiro |
		E clico no botão "Salvar"
        Então vejo mensagem de sucesso "Parecer registrado com sucesso."

	Cenário: Sai do sistema
		Quando acesso o menu "Sair"

	@do_document
	Cenário: Cadastro dos Termos de Autorização
		Dado acesso a página "/"
		Quando realizo o login com o usuário "108012" e senha "abcd"
		E a data do sistema for "30/01/2018"
		E acesso o menu "Pesquisa::Editora::Submissão de Obras::Minhas Obras"
		Então vejo a página "Minhas Obras"
		E vejo o botão "Visualizar"
        Quando clico no botão "Visualizar"
		Então vejo a página "Visualizar Obra: título da obra"
		Quando clico na aba "Termos de Autorização"
		Então vejo os seguintes campos no formulário
			| Campo                                                 | Tipo     |
			| Termos de Autorização de Publicação                   | Arquivo  |
			| Termo de cessão de Direitos Autorais                  | Arquivo |
		E vejo o botão "Salvar"
        Quando preencho o formulário com os dados
			| Campo                                                      | Tipo     | Valor      |
			| Termos de Autorização de Publicação                   | Arquivo  |   termo_autorizacao.png |
			| Termo de cessão de Direitos Autorais                  | Arquivo |  termo_cessao.png       |
		E clico no botão "Salvar"
		Então vejo mensagem de sucesso "Envio dos termos realizado com sucesso."

	Cenário: Sai do sistema
		Quando acesso o menu "Sair"

	@do_document
	Cenário: Validação dos Termos de Autorização
		Dado acesso a página "/"
        Quando realizo o login com o usuário "108007" e senha "abcd"
		E acesso o menu "Pesquisa::Editora::Submissão de Obras::Obras Submetidas"
		Então vejo a página "Obras"
		Quando olho a linha "título da obra"
		E clico no ícone de exibição
        Então vejo a página "Visualizar Obra: título da obra"
		Quando clico na aba "Termos de Autorização"
		Então vejo o botão "Validar Termos de Autorização"
		Quando clico no botão "Validar Termos de Autorização"
		Então vejo a página "Validar os Termos"
		E vejo os seguintes campos no formulário
			| Campo                                                                 | Tipo     |
			| Termo de Autorização de Publicação                                    | Lista    |
			| Termo de cessão de Direitos Autorais                                  | Lista    |
			| Termo de Uso de Imagem, Voz e Texto                                   | Lista    |
			| Termo de Autorização para uso de Nome de Menor                        | Lista    |
			| Contrato de Cessão e Transferência de Direitos Patrimoniais de Autor  | Lista    |
			| Termo de Autorização para uso de Imagem e Fotografia                  | Lista    |
		E vejo o botão "Salvar"
        Quando preencho o formulário com os dados
            | Campo                                                                | Tipo  | Valor |
            | Termo de Autorização de Publicação                                   | Lista | Sim   |
            | Termo de cessão de Direitos Autorais                                 | Lista | Sim   |
            | Termo de Uso de Imagem, Voz e Texto                                  | Lista | Sim   |
            | Termo de Autorização para uso de Nome de Menor                       | Lista | Sim   |
            | Contrato de Cessão e Transferência de Direitos Patrimoniais de Autor | Lista | Sim   |
            | Termo de Autorização para uso de Imagem e Fotografia                 | Lista | Sim   |
		E clico no botão "Salvar"
        Então vejo mensagem de sucesso "Termos validados com sucesso."

	@do_document
	Cenário: Indicação do Revisor
		Dado acesso a página "/"
		Quando a data do sistema for "03/02/2018"
		E acesso o menu "Pesquisa::Editora::Submissão de Obras::Obras Submetidas"
		Então vejo a página "Obras"
		Quando olho a linha "título da obra"
		E clico no ícone de exibição
        Então vejo a página "Visualizar Obra: título da obra"
		Quando clico na aba "Revisão Linguística, Textual e Normalização"
		Então vejo o botão "Indicar Revisor"
		Quando clico no botão "Indicar Revisor"
		Então vejo a página "Indicar Revisor"
		E vejo os seguintes campos no formulário
			| Campo                                             | Tipo     |
			| Usuário                                           | Autocomplete multiplo    |
		E vejo o botão "Enviar"
        Quando preencho o formulário com os dados
			| Campo                                                      | Tipo     | Valor                 |
			| Usuário                                    | Autocomplete multiplo    | Revisor Editora         |
		E clico no botão "Enviar"
        Então vejo mensagem de sucesso "Revisor indicado com sucesso."

	Cenário: Sai do sistema
		Quando acesso o menu "Sair"

	@do_document
	Cenário: Revisão da Obra
		Dado acesso a página "/"
		Quando realizo o login com o usuário "108009" e senha "abcd"
		E acesso o menu "Pesquisa::Editora::Submissão de Obras::Obras Submetidas"
        Então vejo a página "Obras"
        Quando olho a linha "título da obra"
		E clico no ícone de exibição
        Então vejo a página "Visualizar Obra: título da obra"
		Quando clico na aba "Revisão Linguística, Textual e Normalização"
		Então vejo o botão "Revisar Obra"
		Quando clico no botão "Revisar Obra"
		Então vejo a página "Revisar Obra"
		E vejo os seguintes campos no formulário
			| Campo                                             | Tipo     |
			| Obra Revisada                                     | Arquivo  |
			| Link da Obra Revisada                             | Texto    |
			| Observações do Revisor                            | TextArea    |
		E vejo o botão "Salvar"
        Quando preencho o formulário com os dados
			| Campo                                                      | Tipo     | Valor                 |
			| Obra Revisada                                     | Arquivo  | obra_revisada.png              |
			| Link da Obra Revisada                             | Texto    | link_da_obra                   |
			| Observações do Revisor                            | TextArea    | observacoes do revisor      |
		E clico no botão "Salvar"
        Então vejo mensagem de sucesso "Revisão salva com sucesso."

	Cenário: Sai do sistema
		Quando acesso o menu "Sair"

	@do_document
	Cenário: Envio das Correções Após a Revisão
		Dado acesso a página "/"
		Quando realizo o login com o usuário "108012" e senha "abcd"
		E acesso o menu "Pesquisa::Editora::Submissão de Obras::Minhas Obras"
		Então vejo a página "Minhas Obras"
		E vejo o botão "Visualizar"
        Quando clico no botão "Visualizar"
		Então vejo a página "Visualizar Obra: título da obra"
		Quando clico na aba "Revisão Linguística, Textual e Normalização"
		Então vejo o botão "Enviar Correção"
		Quando clico no botão "Enviar Correção"
		Então vejo a página "Enviar Revisão do Autor"
		E vejo os seguintes campos no formulário
			| Campo                                                 | Tipo     |
			| Obra Revisada pelo Autor                              | Arquivo  |
		E vejo o botão "Salvar"
        Quando preencho o formulário com os dados
			| Campo                                                 | Tipo     | Valor      |
			| Obra Revisada pelo Autor                              | Arquivo  | obra_revisada_pelo_autor.png |
		E clico no botão "Salvar"
		Então vejo mensagem de sucesso "Correções enviadas com sucesso."

	Cenário: Sai do sistema
		Quando acesso o menu "Sair"

	@do_document
	Cenário: Emissão do Parecer sobre a Revisão do Autor
		Dado acesso a página "/"
        Quando realizo o login com o usuário "108009" e senha "abcd"
		E acesso o menu "Pesquisa::Editora::Submissão de Obras::Obras Submetidas"
		Então vejo a página "Obras"
		Quando olho a linha "título da obra"
		E clico no ícone de exibição
        Então vejo a página "Visualizar Obra: título da obra"
		Quando clico na aba "Revisão Linguística, Textual e Normalização"
		Então vejo o botão "Emitir Parecer"
		Quando clico no botão "Emitir Parecer"
		Então vejo a página "Emitir Parecer da Revisão"
		E vejo os seguintes campos no formulário
			| Campo                                             | Tipo     |
			| Parecer do Revisor                                | TextArea  |
			| Versão Final da Revisão                             | Arquivo    |
		E vejo o botão "Salvar"
        Quando preencho o formulário com os dados
			| Campo                                                      | Tipo     | Valor                         |
			| Parecer do Revisor                                         | TextArea  | Parecer final do revisor     |
			| Versão Final da Revisão                                    | Arquivo    | versao_final_da_revisao.png |
		E clico no botão "Salvar"
        Então vejo mensagem de sucesso "Parecer salvo com sucesso."

	Cenário: Sai do sistema
		Quando acesso o menu "Sair"

	@do_document
	Cenário: Indicação do Diagramador
		Dado acesso a página "/"
        Quando realizo o login com o usuário "108007" e senha "abcd"
		E a data do sistema for "06/02/2018"
		E acesso o menu "Pesquisa::Editora::Submissão de Obras::Obras Submetidas"
		Então vejo a página "Obras"
		Quando olho a linha "título da obra"
		E clico no ícone de exibição
        Então vejo a página "Visualizar Obra: título da obra"
		Quando clico na aba "Diagramação"
		Então vejo o botão "Indicar Diagramador"
		Quando clico no botão "Indicar Diagramador"
		Então vejo a página "Indicar Diagramador"
		E vejo os seguintes campos no formulário
			| Campo                                             | Tipo     |
			| Usuário                                           | Autocomplete multiplo    |
		E vejo o botão "Enviar"
        Quando preencho o formulário com os dados
			| Campo                                                      | Tipo     | Valor                 |
			| Usuário                                    | Autocomplete multiplo    | Diagramador Editora        |
		E clico no botão "Enviar"
        Então vejo mensagem de sucesso "Diagramador indicado com sucesso."

	Cenário: Sai do sistema
		Quando acesso o menu "Sair"

	@do_document
	Cenário: Diagramação da Obra
		Dado acesso a página "/"
        Quando realizo o login com o usuário "108010" e senha "abcd"
		E a data do sistema for "07/02/2018"
		E acesso o menu "Pesquisa::Editora::Submissão de Obras::Obras Submetidas"
		Então vejo a página "Obras"
		Quando olho a linha "título da obra"
		E clico no ícone de exibição
        Então vejo a página "Visualizar Obra: título da obra"
		Quando clico na aba "Diagramação"
		Então vejo o botão "Cadastrar Diagramação"
		Quando clico no botão "Cadastrar Diagramação"
		Então vejo a página "Cadastrar Diagramação"
		E vejo os seguintes campos no formulário
			| Campo                                             | Tipo     |
			| Diagramação da Capa - Anais                       | Arquivo  |
			| Diagramação do Miolo - Anais                      | Arquivo    |
		E vejo o botão "Salvar"
        Quando preencho o formulário com os dados
			| Campo                                                      | Tipo     | Valor                 |
			| Diagramação da Capa - Anais                                | Arquivo  | diagramacao_capa.png              |
			| Diagramação do Miolo - Anais                               | Arquivo  | diagramacao_miolo.png                   |
		E clico no botão "Salvar"
        Então vejo mensagem de sucesso "Diagramação cadastrada com sucesso."

	Cenário: Sai do sistema
		Quando acesso o menu "Sair"

	@do_document
	Cenário: Avaliação da Diagramação
		Dado acesso a página "/"
		Quando realizo o login com o usuário "108012" e senha "abcd"
		E acesso o menu "Pesquisa::Editora::Submissão de Obras::Minhas Obras"
		Então vejo a página "Minhas Obras"
		E vejo o botão "Visualizar"
        Quando clico no botão "Visualizar"
		Então vejo a página "Visualizar Obra: título da obra"
		Quando clico na aba "Diagramação"
		Então vejo o botão "Avaliar Diagramação"
		Quando clico no botão "Avaliar Diagramação"
		Então vejo a página "Avaliar Diagramação"
		E vejo os seguintes campos no formulário
			| Campo                                                 | Tipo     |
			| Aprovar Capa - Anais                                 | Lista  |
			| Aprovar Miolo - Anais                                 | Lista  |
		E vejo o botão "Salvar"
        Quando preencho o formulário com os dados
			| Campo                                                 | Tipo     | Valor      |
			| Aprovar Capa - Anais                                 | Lista  | Sim         |
			| Aprovar Miolo - Anais                                 | Lista  | Sim        |
		E clico no botão "Salvar"
		Então vejo mensagem de sucesso "Diagramação avaliada com sucesso."

	Cenário: Sai do sistema
		Quando acesso o menu "Sair"

	@do_document
	Cenário: Cadastro do ISBN da Obra
		Dado acesso a página "/"
        Quando realizo o login com o usuário "108007" e senha "abcd"
		E a data do sistema for "10/02/2018"
		E acesso o menu "Pesquisa::Editora::Submissão de Obras::Obras Submetidas"
		Então vejo a página "Obras"
		Quando olho a linha "título da obra"
		E clico no ícone de exibição
        Então vejo a página "Visualizar Obra: título da obra"
		Quando clico na aba "Cadastro ISBN"
		Então vejo o botão "Cadastrar ISBN"
		Quando clico no botão "Cadastrar ISBN"
		Então vejo a página "Cadastrar ISBN"
		E vejo os seguintes campos no formulário
			| Campo                                             | Tipo     |
			| ISBN (Anais)                                     | Texto  |
		E vejo o botão "Salvar"
        Quando preencho o formulário com os dados
			| Campo                                                      | Tipo     | Valor                 |
			| ISBN (Anais)                                     | Texto  |  ISBN 978 - 85 - 333 - 0227 - 3   |
		E clico no botão "Salvar"
        Então vejo mensagem de sucesso "ISBN cadastrado com sucesso."

	Cenário: Sai do sistema
		Quando acesso o menu "Sair"

	@do_document
	Cenário: Cadastro da Ficha Catalográfica da Obra
		Dado acesso a página "/"
        Quando realizo o login com o usuário "108011" e senha "abcd"
		E acesso o menu "Pesquisa::Editora::Submissão de Obras::Obras Submetidas"
		Então vejo a página "Obras"
		Quando olho a linha "título da obra"
		E clico no ícone de exibição
        Então vejo a página "Visualizar Obra: título da obra"
		Quando clico na aba "Ficha Catalográfica"
		Então vejo o botão "Cadastrar Ficha Catalográfica"
		Quando clico no botão "Cadastrar Ficha Catalográfica"
		Então vejo a página "Cadastrar Ficha Catalográfica"
		E vejo os seguintes campos no formulário
			| Campo                                             | Tipo     |
			| Ficha Catalográfica (Anais)                       | Arquivo  |
		E vejo o botão "Salvar"
        Quando preencho o formulário com os dados
			| Campo                                                      | Tipo     | Valor                 |
			| Ficha Catalográfica (Anais)                       | Arquivo  | ficha_catalografica.png        |
		E clico no botão "Salvar"
        Então vejo mensagem de sucesso "Ficha catalográfica cadastrada com sucesso."

	Cenário: Sai do sistema
		Quando acesso o menu "Sair"

	@do_document
	Cenário: Registro da Publicação
		Dado acesso a página "/"
        Quando realizo o login com o usuário "108007" e senha "abcd"
		E acesso o menu "Pesquisa::Editora::Submissão de Obras::Obras Submetidas"
		Então vejo a página "Obras"
		Quando olho a linha "título da obra"
		E clico no ícone de exibição
        Então vejo a página "Visualizar Obra: título da obra"
		Quando clico na aba "Publicação"
		E olho para a aba "Publicação"
		Então vejo os seguintes campos no formulário
			| Campo                                             | Tipo     |
			| Situação da Publicação                            | Lista    |
			| Número de Cópias                                  | Texto    |
			| Data de Envio para Impressão                      | Data     |
			| Link do Repositório Virtual                       | Texto    |
		E vejo o botão "Salvar"
        Quando preencho o formulário com os dados
			| Campo                                             | Tipo     | Valor                              |
			| Situação da Publicação                            | Lista    | Em Andamento                       |
			| Número de Cópias                                  | Texto    | 100                                |
			| Data de Envio para Impressão                      | Data     | 05/05/2018                         |
			| Link do Repositório Virtual                       | Texto    | http://www.link_repositorio.com.br |
		E clico no botão "Salvar"
        Então vejo mensagem de sucesso "Dados da publicação registrados com sucesso."

	Cenário: Sai do sistema
		Quando acesso o menu "Sair"

	@do_document
	Cenário: Cadastro da Data de Liberação para Repositório Virtual
		Dado acesso a página "/"
		Quando realizo o login com o usuário "108012" e senha "abcd"
		E a data do sistema for "11/02/2018"
		E acesso o menu "Pesquisa::Editora::Submissão de Obras::Minhas Obras"
		Então vejo a página "Minhas Obras"
		E vejo o botão "Visualizar"
        Quando clico no botão "Visualizar"
		Então vejo a página "Visualizar Obra: título da obra"
		Quando clico na aba "Publicação"
		Então vejo os seguintes campos no formulário
			| Campo                                                 | Tipo     |
			| Data de Liberação para Repositório Virtual            | Data   |
		E vejo o botão "Salvar"
        Quando preencho o formulário com os dados
			| Campo                                                 | Tipo     | Valor      |
			| Data de Liberação para Repositório Virtual            | Data   | 05/05/2018   |
		E clico no botão "Salvar"
		Então vejo mensagem de sucesso "Dados da publicação registrados com sucesso."

	Cenário: Sai do sistema
		Quando acesso o menu "Sair"

	@do_document
	Cenário: Finalização dos Dados sobre a Publicação da Obra
		Dado acesso a página "/"
        Quando realizo o login com o usuário "108007" e senha "abcd"
		E a data do sistema for "12/02/2018"
		E acesso o menu "Pesquisa::Editora::Submissão de Obras::Obras Submetidas"
		Então vejo a página "Obras"
		Quando olho a linha "título da obra"
		E clico no ícone de exibição
        Então vejo a página "Visualizar Obra: título da obra"
		Quando clico na aba "Publicação"
		E olho para a aba "Publicação"
		Então vejo os seguintes campos no formulário
			| Campo                                             | Tipo     |
			| Situação da Publicação                            | Lista    |
		E vejo o botão "Salvar"
        Quando preencho o formulário com os dados
			| Campo                                                      | Tipo     | Valor                     |
			| Situação da Publicação                            | Lista    |  Concluída                         |
		E clico no botão "Salvar"
        Então vejo mensagem de sucesso "Dados da publicação registrados com sucesso."

	Cenário: Sai do sistema
		Quando acesso o menu "Sair"

	@do_document
	Cenário: Aprovação da Publicação
		Dado acesso a página "/"
        Quando realizo o login com o usuário "108008" e senha "abcd"
		E a data do sistema for "13/02/2018"
		E acesso o menu "Pesquisa::Editora::Submissão de Obras::Obras Submetidas"
		Então vejo a página "Obras"
		Quando olho a linha "título da obra"
		E clico no ícone de exibição
        Então vejo a página "Visualizar Obra: título da obra"
		Quando clico na aba "Conselho Editorial"
		Então vejo os seguintes campos no formulário
			| Campo                                  | Tipo     |
			| Aprovado                               | Lista    |
			| Observações                            | TextArea    |
		E vejo o botão "Salvar"
        Quando preencho o formulário com os dados
			| Campo                                                      | Tipo     | Valor                     |
			| Aprovado                               | Lista    | Sim                                           |
			| Observações                            | TextArea    | observacoes do conselheiro                 |
		E clico no botão "Salvar"
		Então vejo mensagem de sucesso "Análise da liberação da obra realizada com sucesso."

	Cenário: Sai do sistema
		Quando acesso o menu "Sair"

	@do_document
	Cenário: Conclusão da Publicação da Obra
		Dado acesso a página "/"
        Quando realizo o login com o usuário "108007" e senha "abcd"
		E a data do sistema for "14/02/2018"
		E acesso o menu "Pesquisa::Editora::Submissão de Obras::Obras Submetidas"
		Então vejo a página "Obras"
		Quando olho a linha "título da obra"
		E clico no ícone de exibição
        Então vejo a página "Visualizar Obra: título da obra"
		Quando clico na aba "Conclusão"
		Então vejo o botão "Concluir Obra"
		Quando clico no botão "Concluir Obra"
		Então vejo a página "Concluir Publicação de Obra"
		E vejo os seguintes campos no formulário
			| Campo                                      | Tipo     |
			| Obra Concluída                             | Arquivo    |
		E vejo o botão "Salvar"
        Quando preencho o formulário com os dados
			| Campo                                                      | Tipo     | Valor                     |
			| Obra Concluída                                            | Arquivo   |  versao_final_obra.png    |
		E clico no botão "Salvar"
        Então vejo mensagem de sucesso "Obra concluída com sucesso."