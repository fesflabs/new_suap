# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Fechar Período Letivo
	O encerramento do período letivo atual é uma funcionalidade necessária para habilitar a matrícula do aluno no próximo período letivo.
	Está funcionalidade é realizada de forma automática pelo sistema quando não há pendências nos diários.
	Cenário: Configuração inicial para execução dos cenários do edu
        Dado os cadastros da funcionalidade 001
        E os cadastros da funcionalidade 002
        E os cadastros da funcionalidade 003
        E os cadastros da funcionalidade 004
        E os cadastros da funcionalidade 005
		E acesso a página "/"
        Quando realizo o login com o usuário "100001" e senha "abcd"
		E a data do sistema for "20/07/2019"

	@do_document
	Cenário: Forçar Fechar Período
		O administrador acadêmico tem o poder de forçar o fechamento do período letivo de alunos que não podem ter seu período letivo fechado por conta de pendências nos diários.
		Em caso de fechamento forçado a situação do aluno no período letivo ficará em dependência ou reprovado.
		Quando pesquiso por "Fechar Período" e acesso o menu "Ensino::Procedimentos de Apoio::Fechar Período"
        E preencho o formulário com os dados
            | Campo          | Tipo         | Valor |
            | Ano Letivo     | lista        | 2019 |
        	| Período Letivo | lista        | 1 |
        	| Tipo           | checkbox multiplo | Por Turma |
        	| Turma          | autocomplete | 20191.1.10101.1M |
		E clico no botão "Continuar"
		E preencho o formulário com os dados
            | Campo             | Tipo     | Valor |
            | Forçar fechamento | checkbox | marcar |
        	| Confirmado        | checkbox | marcar |
        E clico no botão "Finalizar"
        Então vejo mensagem de sucesso "Período fechado com sucesso."

	Cenário: Autenticar como Secretário Acadêmico
      	Quando acesso o menu "Sair"
		Dado acesso a página "/"
        Quando realizo o login com o usuário "100002" e senha "abcd"

	@do_document
	Cenário: Reabrir Período
		O secretário acadêmico pode reabrir o período letivo de um aluno, turma, curso ou diário para ajustes no lançamento de notas, aulas e faltas.
		Quando pesquiso por "Reabrir Período" e acesso o menu "Ensino::Procedimentos de Apoio::Reabrir Período"
        E preencho o formulário com os dados
            | Campo          | Tipo         | Valor |
            | Ano Letivo     | lista        | 2019 |
        	| Período Letivo | lista        | 1 |
        	| Tipo           | checkbox multiplo | Por Turma |
        	| Turma          | autocomplete | 20191.1.10101.1M |
		E clico no botão "Continuar"
		E preencho o formulário com os dados
            | Campo             | Tipo     | Valor |
        	| Confirmado        | checkbox | marcar |
        E clico no botão "Finalizar"
        Então vejo mensagem de sucesso "Período aberto com sucesso."

	@do_document
	Cenário: Alterar Posse do Diário
		O secretário acadêmico pode transferir a posse da etapa do diário para que o professor realize os ajustes necessários e também retirar a posse do professor.
		Quando pesquiso por "Diários" e acesso o menu "Ensino::Turmas e Diários::Diários"
		E olho a linha "POS.0003"
        E clico no ícone de exibição
		E clico no link "Transferir para o Professor"
		Então vejo mensagem de sucesso "Posse transferida com sucesso"
		Quando clico no link "Transferir para o Registro"
		Então vejo mensagem de sucesso "Posse transferida com sucesso"

	@do_document
	Cenário: Registrar Aula (em posse do registro)
		Quando clico no link "Registrar Aula/Falta"
		E clico no botão "Adicionar Aula"
		E olho para o popup
		E preencho o formulário com os dados
            | Campo      | Tipo     | Valor |
            | Quantidade | texto    | 60 |
            | Etapa      | lista    | Primeira |
            | Data       | Data     | 21/03/2019 |
            | Conteúdo   | textarea | Apresentação da disciplina |
        E clico no botão "Salvar"
        Então vejo mensagem de sucesso "Aula cadastrada/atualizada com sucesso."

	@do_document
	Cenário: Lançar Nota (em posse do registro)
		Quando pesquiso por "Diários" e acesso o menu "Ensino::Turmas e Diários::Diários"
		E olho a linha "POS.0003"
        E clico no ícone de exibição
		E clico na aba "Registro de Notas/Conceitos"
		E olho para o quadro "Registro de Notas"
		Dado acesso a página "/edu/registrar_nota_ajax/3/80"

	@do_document
	Cenário: Fechar Período
		Após correção das pendências no período letivo o secretário acadêmico poderá fechar o período letivo manualmente ou aguardar a execução da rotina automatizada de fechamento.
		Dado acesso a página "/"
		Quando pesquiso por "Fechar Período" e acesso o menu "Ensino::Procedimentos de Apoio::Fechar Período"
        E preencho o formulário com os dados
            | Campo          | Tipo         | Valor |
            | Ano Letivo     | lista        | 2019 |
        	| Período Letivo | lista        | 1 |
        	| Tipo           | checkbox multiplo | Por Turma |
        	| Turma          | autocomplete | 20191.1.10101.1M |
		E clico no botão "Continuar"
		E preencho o formulário com os dados
            | Campo             | Tipo     | Valor |
        	| Confirmado        | checkbox | marcar |
        E clico no botão "Finalizar"
        Então vejo mensagem de sucesso "Período fechado com sucesso."
