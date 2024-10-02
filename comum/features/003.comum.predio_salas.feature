# -*- coding: utf-8 -*-
# language: pt

Funcionalidade: Cadastro Gerais de Prédios e Salas

Cenário: Adicionando o usuário necessário para o teste
    Dado os seguintes usuários
      | Nome                | Matrícula | Setor | Lotação | Email                        | CPF            | Senha | Grupo               |
      | Coordenador Sede    |    225147 | CZN   | CZN     | coord_sede@ifrn.edu.br       | 988.868.680-14 | abcd  | Coordenador da Sede |
    Dado acesso a página "/"

Cenário: Efetuar login no sistema
Quando realizo o login com o usuário "225147" e senha "abcd"

Cenário: Cadastrar Acabamento Externo (Fachada) - Prédio
Quando acesso o menu "Administração::Prédios e Salas::Cadastros::Prédios::Acabamento Externo"
Então vejo o botão "Adicionar Acabamento Externo (Fachada)"
Quando clico no botão "Adicionar Acabamento Externo (Fachada)"
Então vejo a página "Adicionar Acabamento Externo (Fachada)"
Quando preencho o formulário com os dados
| Campo       | Tipo      | Valor   |
| Descrição   | Texto     | Pintura |
| Ativo       | Checkbox  | Marcar  |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

Cenário: Cadastrar Cobertura - Prédio
Quando acesso o menu "Administração::Prédios e Salas::Cadastros::Prédios::Cobertura"
Então vejo o botão "Adicionar Cobertura"
Quando clico no botão "Adicionar Cobertura"
Então vejo a página "Adicionar Cobertura"
Quando preencho o formulário com os dados
| Campo     | Tipo     | Valor                   |
| Descrição | Texto    | Laje impermeabilizada   |
| Ativo     | Checkbox | Marcar                  |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

Cenário: Cadastrar Estrutura - Prédio
Quando acesso o menu "Administração::Prédios e Salas::Cadastros::Prédios::Estrutura"
Então vejo o botão "Adicionar Estrutura"
Quando clico no botão "Adicionar Estrutura"
Então vejo a página "Adicionar Estrutura"
Quando preencho o formulário com os dados
| Campo     | Tipo     | Valor                |
| Descrição | Texto    | Alvenaria estrutural |
| Ativo     | Checkbox | Marcar               |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

Cenário: Cadastrar Sistema de Abastecimento - Prédio
Quando acesso o menu "Administração::Prédios e Salas::Cadastros::Prédios::Sistema de Abastecimento"
Então vejo o botão "Adicionar Sistema de Abastecimento"
Quando clico no botão "Adicionar Sistema de Abastecimento"
Então vejo a página "Adicionar Sistema de Abastecimento"
Quando preencho o formulário com os dados
| Campo     | Tipo     | Valor           |
| Descrição | Texto    | Concessionária	 |
| Ativo     | Checkbox | Marcar          |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

Cenário: Cadastrar Sistema de Alimentação Elétrica - Prédio
Quando acesso o menu "Administração::Prédios e Salas::Cadastros::Prédios::Sistema de Alimentação Elétrica"
Então vejo o botão "Adicionar Sistema de Alimentação Elétrica"
Quando clico no botão "Adicionar Sistema de Alimentação Elétrica"
Então vejo a página "Adicionar Sistema de Alimentação Elétrica"
Quando preencho o formulário com os dados
| Campo     | Tipo     | Valor                       |
| Descrição | Texto    | Transformador individual	 |
| Ativo     | Checkbox | Marcar                      |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

Cenário: Cadastrar Sistema de Proteção de Descarga Atmosférica - Prédio
Quando acesso o menu "Administração::Prédios e Salas::Cadastros::Prédios::Sistema de Proteção de Descarga Atmosférica"
Então vejo o botão "Adicionar Sistema de Proteção Contra Descargas Atmosféricas"
Quando clico no botão "Adicionar Sistema de Proteção Contra Descargas Atmosféricas"
Então vejo a página "Adicionar Sistema de Proteção Contra Descargas Atmosféricas"
Quando preencho o formulário com os dados
| Campo     | Tipo     | Valor   |
| Descrição | Texto    | Possui	 |
| Ativo     | Checkbox | Marcar  |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

Cenário: Cadastrar Sistema Sanitário - Prédio
Quando acesso o menu "Administração::Prédios e Salas::Cadastros::Prédios::Sistema Sanitário"
Então vejo o botão "Adicionar Sistema Sanitário"
Quando clico no botão "Adicionar Sistema Sanitário"
Então vejo a página "Adicionar Sistema Sanitário"
Quando preencho o formulário com os dados
| Campo     | Tipo     | Valor                       |
| Descrição | Texto    | Conectado à rede municipal	 |
| Ativo     | Checkbox | Marcar                      |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

Cenário: Cadastrar Vedação - Prédio
Quando acesso o menu "Administração::Prédios e Salas::Cadastros::Prédios::Vedação"
Então vejo o botão "Adicionar Vedação"
Quando clico no botão "Adicionar Vedação"
Então vejo a página "Adicionar Vedação"
Quando preencho o formulário com os dados
| Campo     | Tipo     | Valor               |
| Descrição | Texto    | Elemento vazado	 |
| Ativo     | Checkbox | Marcar              |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

Cenário: Realizar o cadastro de Prédio 
Quando acesso o menu "Administração::Prédios e Salas::Prédios"
E clico no botão "Adicionar Prédio"
E preencho o formulário com os dados
| Campo  | Tipo         | Valor    |
| Nome   | Texto        | Predio 2 |
| Campus | AutoComplete | CZN      |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

Cenário: Atualização de Prédio
Quando olho para a listagem
E olho a linha "Predio 2"
E clico no link "Predio 2"
Então vejo a página "Editar Predio 2"
Quando preencho o formulário com os dados
| Campo                                             | Tipo                   | Valor                             |
| Nome                                              | Texto                  | Predio 3	                         |
| Campus                                            | Autocomplete           | CZN                               | 
| Ativo                                             | Checkbox               | Marcar                            |
| Estrutura                                         | Autocomplete Multiplo  | Alvenaria estrutural              |  
| Vedação                                           | Autocomplete Multiplo  | Elemento vazado                   |        
| Cobertura                                         | Autocomplete Multiplo  | Laje impermeabilizada             | 
| Sistema Sanitário                                 | Autocomplete Multiplo  | Conectado à rede municipal        | 
| Sistema de Abastecimento                          | Autocomplete Multiplo  | Concessionária                    | 
| Sistema de Alimentação Elétrica                   | Autocomplete Multiplo  | Transformador individual          | 
| Potência do Transformador                         | Texto                  | 22000                             | 
| Informações Adicionais                            | Textarea               | Testando funcionalidade de prédio |
| Sistema de Proteção Contra Descargas Atmosféricas | Autocomplete Multiplo  | Possui                            |  
| Acabamento Externo (Fachadas)                     | Autocomplete Multiplo  | Pintura                           |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Atualização realizada com sucesso."

Cenário: Cadastrar Obra - Predio
Quando acesso o menu "Administração::Prédios e Salas::Prédios"
E olho para a listagem
E olho a linha "Predio 3"
E clico no ícone de exibição
Então vejo a página "Predio 3 (CZN)"
E vejo o botão "Adicionar Obra"
Quando clico no botão "Adicionar Obra"
Então vejo a página "Adicionar obra"
Quando preencho o formulário com os dados
| Campo                   | Tipo         | Valor                |
| Prédio                  | Autocomplete | Predio 3             |
| Tipo da Obra            | lista        | Original             |
| Início da Obra          | Data         | 04/05/2002           |
| Descrição do Escopo     | Textarea     | Prédio recebido      |
| Recebimento Definitivo  | Data         | 04/05/2010           |                                      
| Área Construída         | Texto        | 30000                | 
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

Cenário: Cadastrar Combate a Incêndio e Pânico - Prédio
Quando acesso o menu "Administração::Prédios e Salas::Prédios"
E olho para a listagem
E olho a linha "Predio 3"
E clico no ícone de exibição
Então vejo a página "Predio 3 (CZN)"
E vejo o botão "Adicionar Combate a Incêndio e Pânico"
Quando clico no botão "Adicionar Combate a Incêndio e Pânico"
Então vejo a página "Adicionar Combate a Incêndio e Pânico"
Quando preencho o formulário com os dados
| Campo                   | Tipo         | Valor          |
| Prédio                  | Autocomplete | Predio 3       |
| Protocolo PSCIP         | Texto        | 2022.123456789 |
| Vistoria Técnica        | Data         | 04/05/2002     |
| Validade do Alvará      | Data         | 04/05/2010     |
| Alvará                  | Arquivo      | arquivo.pdf    |
| Observações             | Textarea     | Testando.      |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

Cenário: Cadastrar Acabamentos das Paredes - Sala
Quando acesso o menu "Administração::Prédios e Salas::Cadastros::Salas::Acabamento das Paredes"
Então vejo o botão "Adicionar Acabamento da Parede"
Quando clico no botão "Adicionar Acabamento da Parede"
Então vejo a página "Adicionar Acabamento da Parede"
Quando preencho o formulário com os dados
| Campo       | Tipo      | Valor   |
| Descrição   | Texto     | Pintura |
| Ativo       | Checkbox  | Marcar  |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

Cenário: Cadastrar Classificações - Sala
Quando acesso o menu "Administração::Prédios e Salas::Cadastros::Salas::Classificação"
Então vejo o botão "Adicionar Classificação"
Quando clico no botão "Adicionar Classificação"
Então vejo a página "Adicionar Classificação"
Quando preencho o formulário com os dados
| Campo                 | Tipo     | Valor                                                                                                                                                                                  |
| Descrição             | Texto    | Área de escritório – para o trabalho individual                                                                                                                                        |
| Descrição Expandida   | Textarea | Área útil destinada ao expediente contínuo e composta por estações de trabalho exclusivas, destinada ao trabalho de servidores, empregados, colaboradores, estagiários e terceirizados;|
| Ativo                 | Checkbox | Marcar                                                                                                                                                                                 |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

Cenário: Cadastrar Climatizações - Sala
Quando acesso o menu "Administração::Prédios e Salas::Cadastros::Salas::Climatização"
Então vejo o botão "Adicionar Climatização"
Quando clico no botão "Adicionar Climatização"
Então vejo a página "Adicionar Climatização"
Quando preencho o formulário com os dados
| Campo       | Tipo      | Valor           |
| Descrição   | Texto     | Não Climatizado |
| Ativo       | Checkbox  | Marcar          |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

Cenário: Cadastrar Esquadrias - Sala
Quando acesso o menu "Administração::Prédios e Salas::Cadastros::Salas::Esquadrias"
Então vejo o botão "Adicionar Esquadria"
Quando clico no botão "Adicionar Esquadria"
Então vejo a página "Adicionar Esquadria"
Quando preencho o formulário com os dados
| Campo       | Tipo      | Valor    |
| Descrição   | Texto     | Alumínio |
| Ativo       | Checkbox  | Marcar   |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."


Cenário: Cadastrar Forros - Sala
Quando acesso o menu "Administração::Prédios e Salas::Cadastros::Salas::Forro"
Então vejo o botão "Adicionar Forro"
Quando clico no botão "Adicionar Forro"
Então vejo a página "Adicionar Forro"
Quando preencho o formulário com os dados
| Campo       | Tipo      | Valor           |
| Descrição   | Texto     | Pintura em Laje |
| Ativo       | Checkbox  | Marcar          |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

Cenário: Cadastrar Instalação de Gases - Sala
Quando acesso o menu "Administração::Prédios e Salas::Cadastros::Salas::Instalação de Gases"
Então vejo o botão "Adicionar Instalação de Gases"
Quando clico no botão "Adicionar Instalação de Gases"
Então vejo a página "Adicionar Instalação de Gases"
Quando preencho o formulário com os dados
| Campo       | Tipo      | Valor  |
| Descrição   | Texto     | GLP    |
| Ativo       | Checkbox  | Marcar |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

Cenário: Cadastrar Instalação Elétricas - Sala
Quando acesso o menu "Administração::Prédios e Salas::Cadastros::Salas::Instalação Elétrica"
Então vejo o botão "Adicionar Instalação Elétrica"
Quando clico no botão "Adicionar Instalação Elétrica"
Então vejo a página "Adicionar Instalação Elétrica"
Quando preencho o formulário com os dados
| Campo       | Tipo      | Valor       |
| Descrição   | Texto     | Embutida    |
| Ativo       | Checkbox  | Marcar      |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

Cenário: Cadastrar Instalação hidraulica - Sala
Quando acesso o menu "Administração::Prédios e Salas::Cadastros::Salas::Instalação Hidráulica"
Então vejo o botão "Adicionar Instalação Hidráulica"
Quando clico no botão "Adicionar Instalação Hidráulica"
Então vejo a página "Adicionar Instalação Hidráulica"
Quando preencho o formulário com os dados
| Campo       | Tipo      | Valor       |
| Descrição   | Texto     | Aparente    |
| Ativo       | Checkbox  | Marcar      |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

Cenário: Cadastrar Instalação Lógica - Sala
Quando acesso o menu "Administração::Prédios e Salas::Cadastros::Salas::Instalação Lógica"
Então vejo o botão "Adicionar Instalação de Lógica"
Quando clico no botão "Adicionar Instalação de Lógica"
Então vejo a página "Adicionar Instalação de Lógica"
Quando preencho o formulário com os dados
| Campo       | Tipo      | Valor       |
| Descrição   | Texto     | Não possui  |
| Ativo       | Checkbox  | Marcar      |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

Cenário: Cadastrar Instalação de Pisos - Sala
Quando acesso o menu "Administração::Prédios e Salas::Cadastros::Salas::Piso"
Então vejo o botão "Adicionar Piso"
Quando clico no botão "Adicionar Piso"
Então vejo a página "Adicionar Piso"
Quando preencho o formulário com os dados
| Campo       | Tipo      | Valor     |
| Descrição   | Texto     | Cerâmico  |
| Ativo       | Checkbox  | Marcar    |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

Cenário: Cadastrar Uso da Sala
Quando acesso o menu "Administração::Prédios e Salas::Cadastros::Salas::Uso da Sala"
Então vejo o botão "Adicionar Uso da Sala"
Quando clico no botão "Adicionar Uso da Sala"
Então vejo a página "Adicionar Uso da Sala"
Quando preencho o formulário com os dados
| Campo       | Tipo      | Valor     |
| Descrição   | Texto     | Extensão  |
| Ativo       | Checkbox  | Marcar    |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

Cenário: Cadastrar Sala
Quando acesso o menu "Administração::Prédios e Salas::Salas"
Então vejo o botão "Adicionar Sala"
Quando clico no botão "Adicionar Sala"
Então vejo a página "Adicionar Sala"
Quando preencho o formulário com os dados
| Campo                                       | Tipo                  | Valor              |
| Nome                                        | Texto                 | Sala 2             |
| Prédio                                      | Autocomplete          | Predio 3           |
| Capacidade da sala (em número de pessoas)   | Texto                 | 150                |
| Setores                                     | Autocomplete Multiplo | A0                 |
| Ativa                                       | Checkbox              | Marcar             |
| Agendável                                   | Checkbox              | Marcar             |  
| Agendamento apenas por servidores do campus | Checkbox              | Marcar             |
| Informações complementares                  | Textarea              | Testando           |
| Área Útil                                   | Texto                 | 200000             |
| Área de Parede                              | Texto                 | 450000             |
| Uso da sala                                 | Autocomplete          | Extensão           |
| Classificação                               | Autocomplete          | Área de escritório |
| Instalação Elétrica                         | Autocomplete Multiplo | Embutida           |
| Instalação de Lógica                        | Autocomplete Multiplo | Não possui         |
| Instalação Hidráulica                       | Autocomplete Multiplo | Aparente           |
| Instalação de Gases                         | Autocomplete Multiplo | GLP                |
| Climatização                                | Autocomplete Multiplo | Não Climatizado    |
| Acabamento das Paredes                      | Autocomplete Multiplo | Pintura            |
| Piso                                        | Autocomplete Multiplo | Cerâmico           |
| Forro                                       | Autocomplete Multiplo | Pintura em Laje    |
| Esquadrias                                  | Autocomplete Multiplo | Alumínio           |
E clico no botão "Salvar"
Então vejo mensagem de sucesso "Cadastro realizado com sucesso."

