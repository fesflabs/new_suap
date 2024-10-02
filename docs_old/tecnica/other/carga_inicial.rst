:orphan:

SOBRE A IMPORTAÇÃO

Chamamos de importação o processo de se retirar alguns dados pessoais e funcionais dos servidores federais presentes no Sistema Integrado de Administração de Recursos Humanos (SIAPE) e inseri-los mo Sistema Unificado de Administração Pública (SUAP).

A importação consiste de duas fases: A extração dos arquivos do SIAPE e o upload desses mesmos para o SUAP.

Antes de prosseguir, é interessante ler o Manual do Usuário do Extrator de Dados – SIAPE, disponível para download (apenas usuários do sistema) no Portal Siapenet para familizarizar-se com a utilização da extração. Como resultado da extração, são gerados dois tipos de arquivos. Um com extensão TXT e o segundo com extensão REF. O arquivo TXT contém todos os dados propriamente ditos. O arquivo REF descreve o layout de como as informações estão distribuídas no arquivo TXT (metadados). Devido às limitações de acesso ao SIAPE e a quantidade de servidores hoje presente no IFRN, dividimos a extração semanal em vários arquivos

IMPORTAÇÃO EXTREMAMENTE SIMPLES

Os passos a seguir permitem que a maior parte das aplicações que dependem dos dados do SIAPE (Ponto, Protocolo, Patrimônio, Almoxarifado, Frota, etc) passem a operar no SUAP. Porém alguns dados dos servidores continuarão incompletos até que TODOS os arquivos sejam devidamente importados. Consulte o tópico IMPORÇÃO COMPLETA caso o procedimento a seguir não atenda a suas necessidades.

1 - Acesse o Extrator

2 - Extraia os seguintes campos dos seguintes arquivos 

A)
Arquivo Siape: SIAPE-UNIDADEORGANIZACIONAL:
Campos:
-- IT-IN-STATUS-REGISTRO-TABELA
-- GR-IDENTIFICACAO-UORG
-- IT-NO-UNIDADE-ORGANIZACIONAL
-- IT-SG-UNIDADE-ORGANIZACIONAL
-- IT-CO-UORG-VINCULACAO
Campo Chave: GR-IDENTIFICACAO-UORG
Operador: IN
Faixa: XXXXX000000000 -> XXXXX999999999
Destino da Extração: Portal Online (PO)
Classe Suap: Setor

B)
Arquivo Siape: SIAPE-SERVIDOR-EXTR
Campos:
-------------- Página 1 -----------------

-- GR-MATRICULA

-- IT-NO-SERVIDOR
-- IT-NO-MAE

-- IT-NU-CPF
-- IT-NU-PIS-PASEP

-------------- Página 2 -----------------

-- IT-CO-ESTADO-CIVIL

-------------- Página 3 -----------------

-- IT-SG-REGIME-JURIDICO
-- IT-CO-SITUACAO-SERVIDOR
-- IT-CO-BANCO-PGTO-SERVIDOR
-- IT-CO-AGENCIA-BANCARIA-PGTO-SERV
-- IT-NU-CCOR-PGTO-SERVIDOR

-------------- Página 4 -----------------

-- IT-CO-GRUPO-OCOR-AFASTAMENTO
-- IT-CO-OCOR-AFASTAMENTO
-- IT-DA-INICIO-OCOR-AFASTAMENTO
-- IT-DA-TERMINO-OCOR-AFASTAMENTO
-- IT-CO-DIPL-AFASTAMENTO
-- IT-DA-PUBL-DIPL-AFASTAMENTO
-- IT-NU-DIPL-AFASTAMENTO
-- IT-CO-GRUPO-OCOR-EXCLUSAO

-------------- Página 5 -----------------

-- IT-CO-OCOR-EXCLUSAO
-- IT-DA-OCOR-EXCLUSAO-SERV
-- IT-CO-DIPL-EXCLUSAO
-- IT-DA-PUBL-DIPL-EXCLUSAO
-- IT-NU-DIPL-EXCLUSAO
-- IT-CO-GRUPO-OCOR-INATIVIDADE
-- IT-CO-OCOR-INATIVIDADE
-- IT-DA-OCOR-INATIVIDADE-SERV
-- IT-CO-DIPL-INATIVIDADE
-- IT-DA-PUBL-DIPL-INATIVIDADE
-- IT-NU-DIPL-INATIVIDADE

-------------- Página 7 -----------------

-- IT-CO-GRUPO-CARGO-EMPREGO
-- IT-CO-CARGO-EMPREGO
-- IT-CO-CLASSE

-- IT-CO-PADRAO
-- IT-CO-NIVEL
-- IT-DA-OCUPACAO-CARGO-EMPREGO

-------------- Página 8 -----------------

-- IT-DA-SAIDA-CARGO-EMPREGO

-- IT-CO-UORG-LOTACAO-SERVIDOR
-- IT-DA-LOTACAO

Campo Chave: GR-MATRICULA
Operador: IN
Faixa: XXXXX0000000 -> XXXXX9999999
Com XXXXX = Identificador da Instituição
Destino da Extração: Portal Online (PO)
Classe SUAP: Servidor

3 - Acesse o Portal SiapeNET e efetue o download do 'Arquivo de Dados' com os setores e os servidores

4 - Faça o upload dos setores no SUAP a partir do site administrativo (suap -> setor -> Importar do Arquivo).

5 - Faça o upload dos servidores no SUAP a partir do site administrativo(suap -> servidor -> Importar do arquivo).

IMPORTAÇÂO COMPLETA

Na importação completa, todas as tabelas da base do SUAP serão preenchidas, permitindo precisão em todos os relatórios estatísticos e quantitativos da aplicação RH. Siga os passos 1, 2 e 3 do tópico anterior utilizando os seguintes arquivos do Siape:

A)
Arquivo Siape: SIAPE-UNIDADEORGANIZACIONAL:
Campos:
-- IT-IN-STATUS-REGISTRO-TABELA
-- GR-IDENTIFICACAO-UORG
-- IT-NO-UNIDADE-ORGANIZACIONAL
-- IT-SG-UNIDADE-ORGANIZACIONAL
-- IT-CO-UORG-VINCULACAO
Campo Chave: GR-IDENTIFICACAO-UORG
Operador: IN
Faixa: XXXXX000000000 -> XXXXX999999999
Destino da Extração: Portal Online (PO)
Classe Suap: Setor

B)

Arquivo Siape: SIAPE-ATIVIDADE
Campos:
-- IT-IN-STATUS-REGISTRO-TABELA
-- IT-CO-ATIVIDADE
-- IT-NO-ATIVIDADE
Campo Chave: IT-CO-ATIVIDADE
Operador: IN
Faixa: 0000 -> 9999
Destino da Extração: Portal Online (PO)
Classe Suap: Atividade

C)

Arquivo Siape: SIAPE-GRUPO-CARGO-EMPREGO
Campos:
-- IT-IN-STATUS-REGISTRO-TABELA
-- IT-CO-GRUPO-CARGO-EMPREGO
-- IT-SG-GRUPO-CARGO-EMPREGO
-- IT-NO-GRUPO-CARGO-EMPREGO
Campo Chave: CO-GRUPO-CARGO-EMPREGO
Operador: IN
Faixa: 000 -> 999
Destino da Extração: Portal Online (PO)
Classe Suap: GrupoCargoEmprego

D)

Arquivo Siape: SIAPE-CARGO-EMPREGO
Campos:
-- IT-IN-STATUS-REGISTRO-TABELA
-- GR-IDEN-CARGO-EMPREGO
-- IT-NO-CARGO-EMPREGO
-- IT-SG-ESCOLARIDADE
Campo Chave: GR-IDEN-CARGO-EMPREGO
Operador: IN
Faixa: 000000 -> 999999
Destino da Extração: Portal Online (PO)
Classe Suap: CargoEmprego

E)

Arquivo Siape: SIAPE-CLASSE
Campos:
-- IT-IN-STATUS-REGISTRO-TABELA
-- IT-CO-CLASSE
-- IT-NO-CLASSE
Campo Chave: IT-CO-CLASSE
Operador: IN
Faixa: 0 -> Z ou A -> 9 (vou verificar)
Destino da Extração: Portal Online (PO)
Classe Suap: ClasseCargo

F)

Arquivo Siape: SIAPE-DIPLOMA-LEGAL
Campos:
-- IT-IN-STATUS-REGISTRO-TABELA
-- IT-CO-DIPLOMA-LEGAL
-- IT-SG-DIPLOMA-LEGAL
-- IT-NO-DIPLOMA-LEGAL
Campo Chave: IT-CO-DIPLOMA-LEGAL
Operador: IN
Faixa: 00 -> 99
Destino da Extração: Portal Online (PO)
Classe Suap: DiplomaLegal

G)

Arquivo Siape: SIAPE-ESTADO-CIVIL
Campos:
-- IT-IN-STATUS-REGISTRO-TABELA
-- IT-CO-ESTADO-CIVIL
-- IT-NO-ESTADO-CIVIL
Campo Chave: IT-CO-ESTADO-CIVIL
Operador: IN
Faixa: 0 -> 9
Destino da Extração: Portal Online (PO)
Classe Suap: EstadoCivil

H)

Arquivo Siape: SIAPE-UF
Campos:
-- IT-IN-STATUS-REGISTRO-TABELA
-- IT-SG-UF
-- IT-NO-UF
Campo Chave: IT-SG-UF
Operador: IN
Faixa: AA -> ZZ
Destino da Extração: Portal Online (PO)
Classe Suap: UnidadeFederativa

I)

Arquivo Siape: SIAPE-FUNCAO
Campos:
-- IT-IN-STATUS-REGISTRO-TABELA
-- IT-SG-FUNCAO
-- IT-NO-FUNCAO
Campo Chave: IT-SG-FUNCAO
Operador: IN
Faixa: AAA -> ZZZ
Destino da Extração: Portal Online (PO)
Classe Suap: Funcao

J)

Arquivo Siape: SIAPE-GRUPO-OCORRENCIA
Campos:
-- IT-IN-STATUS-REGISTRO-TABELA
-- IT-CO-GRUPO-OCORRENCIA
-- IT-NO-GRUPO-OCORRENCIA
Classe Suap: GrupoOcorrencia
Operador: IN
Faixa: 00 -> 99
Destino da Extração: Portal Online (PO)
Campo Chave: IT-CO-GRUPO-OCORRENCIA

K)

Arquivo Siape: SIAPE-OCORRENCIA
Campos:
-- IT-IN-STATUS-REGISTRO-TABELA
-- GR-IDEN-OCORRENCIA
-- IT-NO-OCORRENCIA
Campo Chave: GR-IDEN-OCORRENCIA
Operador: IN
Faixa: 00000 -> 99999
Destino da Extração: Portal Online (PO)
Classe Suap: Ocorrencia

L)

Arquivo Siape: SIAPE-JORANDA-TRABALHO
Campos:
-- IT-IN-STATUS-REGISTRO-TABELA
-- IT-CO-JORNADA-TRABALHO
-- IT-NO-JORNADA-TRABALHO
Campo Chave: IT-CO-JORNADA-TRABALHO
Operador: IN
Faixa: 00 -> 99
Destino da Extração: Portal Online (PO)
Classe Suap: JornadaTrabalho

M)

Arquivo Siape: SIAPE-NIVEL-ESCOLARIDADE
Campos:
-- IT-IN-STATUS-REGISTRO-TABELA
-- IT-CO-NIVEL-ESCOLARIDADE
-- IT-NO-NIVEL-ESCOLARIDADE
Campo Chave: IT-CO-NIVEL-ESCOLARIDADE
Operador: IN
Faixa: 00 -> 99
Destino da Extração: Portal Online (PO)
Classe Suap: NivelEscolaridade

N)

Arquivo Siape: SIAPE-PAIS
Campos:
-- IT-IN-STATUS-REGISTRO-TABELA
-- IT-CO-PAIS
-- IT-NO-PAIS
-- IT-IN-PAIS-EQUIPARADO
Campo Chave: IT-CO-PAIS
Operador: IN
Faixa: 000 -> 999
Destino da Extração: Portal Online (PO)
Classe Suap: Pais

O)

Arquivo Siape: SIAPE-REGIME-JURIDICO
Campos:
-- IT-IN-STATUS-REGISTRO-TABELA
-- IT-SG-REGIME-JURIDICO
-- IT-NO-REGIME-JURIDICO
Campo Chave: IT-SG-REGIME-JURIDICO
Operador: IN
Faixa: AAA -> ZZZ
Destino da Extração: Portal Online (PO)
Classe Suap: RegimeJuridico

P)

Arquivo Siape: SIAPE-SITUACAO-SERVIDOR
Campos:
-- IT-IN-STATUS-REGISTRO-TABELA
-- IT-CO-SITUACAO-SERVIDOR
-- IT-NO-SITUACAO-SERVIDOR
Campo Chave: IT-CO-SITUACAO-SERVIDOR
Operador: IN
Faixa: 00 -> 99
Destino da Extração: Portal Online (PO)
Classe Suap: Situacao

Q)

Arquivo Siape: SIAPE-BANCO
Campos:
-- IT-IN-STATUS-REGISTRO-TABELA
-- IT-CO-BANCO
-- IT-NO-BANCO
-- IT-SG-BANCO
Campo Chave: IT-CO-BANCO
Operador: IN
Faixa: 000 -> 999
Destino da Extração: Portal Online (PO)
Classe Suap: Banco

R)

Arquivo Siape: SIAPE-BENEFICIARIO-PENSAO
Campos:
-- IT-DA-ANO-MES-PAGAMENTO
-- IT-NU-MATRICULA-BENEF-PENSAO
-- IT-NO-BENEFICIARIO-PENSAO
-- IT-DA-NASCIMENTO-BENEF-PENSAO
-- IT-NU-CPF
-- IT-CO-SEXO
-- IT-CO-ESTADO-CIVIL
-- IT-QT-DEPENDENTE-IR
-- IT-CO-REGISTRO-GERAL
-- IT-SG-ORGAO-EXPEDIDOR-IDEN
-- IT-DA-EXPEDICAO-IDEN
-- IT-SG-UF-IDEN
-- IT-NO-LOGRADOURO
-- IT-NO-BAIRRO
-- IT-NO-MUNICIPIO
-- IT-CO-CEP
-- IT-NU-TELEFONE
-- IT-SG-UF
-- IT-0CO-ORGAO(1)
-- IT-NU-MATRICULA(1)
-- IT-DA-INICIO-OCOR-PENSAO
-- IT-DA-TERMINO-OCOR-PENSAO
-- IT-NO-MAE
-- IT-ED-CORREIO-ELETRONICO
-- IT-NU-TITULO-ELEITOR
-- IT-SG-UF-TITULO-ELEITOR
-- IT-NU-ZONA-ELEITORAL
-- IT-NU-SECAO-ELEITORAL
-- IT-DA-EMISSAO-TITULO-ELEITOR
Campo Chave: IT-NU-MATRICULA-BENEF-PENSAO e IT-CO-ORGAO(1)
Operador: IN e =
Faixa: 00000000 -> 99999999 e [Código de sua Instituição]
Destino da Extração: Portal Online (PO)
Classe Suap: Pensionista

S)

Arquivo Siape: SIAPE-RUBRICA
Campos:
-- IT-IN-STATUS-REGISTRO-TABELA
-- IT-CO-RUBRICA
-- IT-NO-RUBRICA
Campo Chave: IT-CO-RUBRICA
Operador: IN
Faixa: 0000 -> 9999
Destino da Extração: Portal Online (PO)
Classe Suap: Rubrica

T)

Arquivo Siape: SIAPE-DEPENDENTE-EXTR
Campos:
-- IT-NU-DEPENDENTE
-- IT-NO-DEPENDENTE
-- IT-CO-SEXO
-- GR-MATRICULA-DEPENDENCIA-SERV(1)
-- IT-CO-GRAU-PARENTESCO(1)
-- IT-NO-MAE
-- IT-DA-NASCIMENTO
Campo Chave: GR-MATRICULA-DEPENDENCIA-SERV(1)
Operador: IN
Faixa: XXXXX0000000 -> 264359999999
Destino da Extração: Portal Online (PO)
Classe Suap: Dependente
U)

Arquivo Siape: SIAPE-PARENTESCO
Classe Suap: GrauParentesco

-- IT-IN-STATUS-REGISTRO-TABELA
-- IT-CO-GRAU-PARENTESCO
-- IT-NO-GRAU-PARENTESCO

V)

Arquivo Siape: SIAPE-BENEFICIO
Classe Suap: Beneficio

-- IT-CO-BENEFICIO
-- IT-NO-BENEFICIO
-- IT-IN-STATUS-REGISTRO-TABELA

X)

Arquivo Siape: SIAPE-BENEFICIO-DEPENDENTE
Classe Suap: BeneficioDependente

-- GR-IDENT-BENEFICIO-DEPENDENTE
-- IT-DA-INIC-BENEFICIO-DEPENDENTE
-- IT-DA-TERM-BENEFICIO-DEPENDENTE
-- IT-DA-CADASTRAMENTO-BENEFICIO

2 - Os Dados e Arquivos da Classe Servidor:

A)
Arquivo Siape: SIAPE-SERVIDOR-EXTR
Campos:
-------------- Página 1 -----------------

-- GR-MATRICULA

-- IT-NO-SERVIDOR
-- IT-NO-MAE

-- IT-NU-CPF
-- IT-NU-PIS-PASEP

-------------- Página 2 -----------------

-- IT-CO-ESTADO-CIVIL

-------------- Página 3 -----------------

-- IT-SG-REGIME-JURIDICO
-- IT-CO-SITUACAO-SERVIDOR
-- IT-CO-BANCO-PGTO-SERVIDOR
-- IT-CO-AGENCIA-BANCARIA-PGTO-SERV
-- IT-NU-CCOR-PGTO-SERVIDOR

-------------- Página 4 -----------------

-- IT-CO-GRUPO-OCOR-AFASTAMENTO
-- IT-CO-OCOR-AFASTAMENTO
-- IT-DA-INICIO-OCOR-AFASTAMENTO
-- IT-DA-TERMINO-OCOR-AFASTAMENTO
-- IT-CO-DIPL-AFASTAMENTO
-- IT-DA-PUBL-DIPL-AFASTAMENTO
-- IT-NU-DIPL-AFASTAMENTO
-- IT-CO-GRUPO-OCOR-EXCLUSAO

-------------- Página 5 -----------------

-- IT-CO-OCOR-EXCLUSAO
-- IT-DA-OCOR-EXCLUSAO-SERV
-- IT-CO-DIPL-EXCLUSAO
-- IT-DA-PUBL-DIPL-EXCLUSAO
-- IT-NU-DIPL-EXCLUSAO
-- IT-CO-GRUPO-OCOR-INATIVIDADE
-- IT-CO-OCOR-INATIVIDADE
-- IT-DA-OCOR-INATIVIDADE-SERV
-- IT-CO-DIPL-INATIVIDADE
-- IT-DA-PUBL-DIPL-INATIVIDADE
-- IT-NU-DIPL-INATIVIDADE

-------------- Página 7 -----------------

-- IT-CO-GRUPO-CARGO-EMPREGO
-- IT-CO-CARGO-EMPREGO
-- IT-CO-CLASSE

-- IT-CO-PADRAO
-- IT-CO-NIVEL
-- IT-DA-OCUPACAO-CARGO-EMPREGO

-------------- Página 8 -----------------

-- IT-DA-SAIDA-CARGO-EMPREGO

-- IT-CO-UORG-LOTACAO-SERVIDOR
-- IT-DA-LOTACAO

Campo Chave: GR-MATRICULA
Operador: IN
Faixa: XXXXX0000000 -> XXXXX9999999
Com XXXXX = Identificador da Instituição
Destino da Extração: Portal Online (PO)
Classe SUAP: Servidor

B)
Arquivo Siape: SIAPE-SERVIDOR-EXTR
Campos:
-------------- Página 1 -----------------

GR-MATRICULA

IT-DA-NASCIMENTO

-------------- Página 2 -----------------

IT-CO-SEXO

IT-QT-DEPENDENTE-IR
IT-NU-CARTEIRA-TRABALHO
IT-NU-SERIE-CARTEIRA-TRABALHO
IT-SG-UF-CTRA-SERVIDOR
IT-DA-PRIMEIRO-EMPREGO

IT-DA-CADASTRAMENTO-SERVIDOR

IT-CO-NIVEL-ESCOLARIDADE

-------------- Página 5 -----------------

IT-NU-PROCESSO-APOSENTADORIA
IT-CO-GRUPO-OCOR-INGR-ORGAO

-------------- Página 6 -----------------

IT-CO-OCOR-INGR-ORGAO
IT-DA-OCOR-INGR-ORGAO-SERV
IT-CO-DIPL-INGR-ORGAO
IT-DA-PUBL-DIPL-INGR-ORGAO
IT-NU-DIPL-INGR-ORGAO
IT-CO-GRUPO-OCOR-INGR-SPUB
IT-CO-OCOR-INGR-SPUB
IT-DA-OCOR-INGR-SPUB-SERV
IT-CO-DIPL-INGR-SPUB
IT-DA-PUBL-DIPL-INGR-SPUB
IT-NU-DIPL-INGR-SPUB

-------------- Página 8 -----------------

IT-SG-FUNCAO
IT-CO-NIVEL-FUNCAO
IT-SG-ESCOLARIDADE-FUNCAO
IT-IN-OPCAO-FUNCAO
IT-DA-INGRESSO-FUNCAO
IT-DA-SAIDA-FUNCAO
IT-CO-UORG-FUNCAO
IT-CO-ATIVIDADE-FUNCAO

-------------- Página 9 -----------------

IT-SG-NOVA-FUNCAO
IT-CO-NIVEL-NOVA-FUNCAO
IT-SG-ESCOLARIDADE-NOVA-FUNCAO
IT-IN-OPCAO-NOVA-FUNCAO
IT-DA-INGRESSO-NOVA-FUNCAO
IT-DA-SAIDA-NOVA-FUNCAO
IT-CO-UORG-NOVA-FUNCAO
IT-CO-ATIVIDADE-NOVA-FUNCAO

IT-CO-JORNADA-TRABALHO

-------------- Página 10 ----------------

IT-NU-NUMERADOR-PROP
IT-NU-DENOMINADOR-PROP

Campo Chave: GR-MATRICULA
Operador: IN
Faixa: XXXXX0000000 -> XXXXX9999999
Com XXXXX = Identificador da Instituição
Destino da Extração: Portal Online (PO)
Classe Suap: Servidor

C)
Arquivo Siape: SIAPE-SERVIDOR-EXTR
Campos:
-------------- Página 1 -----------------

GR-MATRICULA

-------------- Página 8 -----------------

IT-CO-VAGA

-------------- Página 11 ----------------

IT-CO-REGISTRO-GERAL
IT-SG-ORGAO-EXPEDIDOR-IDEN
IT-DA-EXPEDICAO-IDEN
IT-SG-UF-IDEN

-------------- Página 12 ----------------

IT-DA-OBITO

-------------- Página 13 ----------------

IT-NU-TITULO-ELEITOR
IT-IN-OPERADOR-RAIOX

IT-CO-GRUPO-OCOR-INGR-SPUB-POSSE
IT-CO-OCOR-INGR-SPUB-POSSE

-------------- Página 14 ----------------

IT-DA-OCOR-INGR-SPUB-POSSE
IT-CO-DIPL-INGR-SPUB-POSSE
IT-DA-PUBL-DIPL-INGR-SPUB-POSSE
IT-NU-DIPL-INGR-SPUB-POSSE

-------------- Página 17 ----------------

IT-NU-SEQ-FORMACAO-RH
IT-CO-TITULACAO-FORMACAO-RH

Campo Chave: GR-MATRICULA
Operador: IN
Faixa: XXXXX0000000 -> XXXXX9999999
Com XXXXX = Identificador da Instituição
Destino da Extração: Portal Online (PO)
Classe Suap: Servidor

D)
Arquivo Siape: SIAPE-SERVIDOR-DISPONIVEL
Campos:
-------------- Página 1 -----------------

GR-MATRICULA-SERV-DISPONIVEL

IT-NO-LOGRADOURO
IT-NO-BAIRRO
IT-NO-MUNICIPIO
IT-CO-CEP
IT-SG-UF-SERV-DISPONIVEL

-------------- Página 2 -----------------

IT-NU-ENDERECO
IT-NU-COMPLEMENTO-ENDERECO
IT-CO-PAIS-ENDERECO
IT-NU-DDD-TELEFONE
IT-NU-TELEFONE
IT-NU-RAMAL-TELEFONE

-------------- Página 3 -----------------

IT-ED-CORREIO-ELETRONICO

IT-SG-GRUPO-SANGUINEO
IT-SG-FATOR-RH

Campo Chave: GR-MATRICULA-SERV-DISPONIVEL
Operador: IN
Faixa: XXXXX0000000 -> XXXXX9999999
Com XXXXX = Identificador da Instituição
Destino da Extração: Portal Online (PO)
Classe Suap: Servidor

E)
Arquivo Siaper: SIPE-U-RH
Campos:
-------------- Página 1 -----------------

NU-CPF-RH

NO-MUNICIPIO-NASCIMENTO-RH

NO-PAI-RH

-------------- Página 2 -----------------

SG-UF-TITULO-ELEITOR-RH

NU-ZONA-ELEITORAL-RH
NU-SECAO-ELEITORAL-RH
DA-EMISSAO-TITULO-ELEITOR-RH

-------------- Página 3 -----------------

NU-CART-MOTORISTA-RH
NU-REGISTRO-CART-MOTORISTA-RH
IN-CATEGORIA-CART-MOTORISTA-RH
SG-UF-CART-MOTORISTA-RH

DA-EXPEDICAO-CART-MOTORISTA-RH
DA-VALIDADE-CART-MOTORISTA-RH

-------------- Página 5 -----------------

ED-FAX-RH

ED-SG-UF-MUNICIPIO-RH

-------------- Página 6 -----------------

CO-IDENT-UNICA-SIAPE-RH

Campo Chave: NU-CPF-RH
Operador: IN
Faixa: 00000000000 -> 99999999999
Campo Chave: ED-SG-UF-MUNICIPIO-RH
Operador: =
Faixa: RN
Destino da Extração: Portal Batch (PO)
Classe Suap: Servidor

F)
Arquivo Siape: SIAPE-SERVIDOR-FERIAS
Campos:
-- GR-MATR-EXERCICIO-FERIAS
-- IT-DA-INICIO-FERIAS
-- IT-QT-DIAS-FERIAS
Campo Chave: MATRICULA-EXERCICIO-FERIAS
Operador: IN
Faixa: XXXXX00000000000 -> XXXXX9999999999
Destino da Extração: Portal Online (PO)
Com XXXXX = Identificador da Instituição
Classe Suap: Servidor

G)
Arquivo Siape: SIAPE-SERVIDOR-FERIAS-HIST
Campos:
-- GR-MATR-EXERCICIO-FERIAS-HIST
-- IT-DA-INICIO-FERIAS
-- IT-QT-DIAS-FERIAS
Campo Chave: MATRICULA-EXERCICIO-FERIAS
Operador: IN
Faixa: XXXXX00000000000000000 -> XXXXX99999999999999999
Destino da Extração: Portal Online (PO)
Com XXXXX = Código da Instituição
Classe Suap: Servidor

H) A classe Contra-cheque é preenchida utilizando um arquivo chamado fita-espelho.

OBSERVAÇÕES FINAIS

Após a finalização de uma importação, um arquivo de log é gerado em suap/rh/logs. Lá pode-se encontrar dados que apontem para a possível solução de algum problema.

O terminal do extrator oferece um recurso de macros que pode eventualmente automatizar parte do processo de importação. Mas os arquivo do extrator mudam com tanta freqüência que ainda estamos estudando a vaibilidade da criação de uma macro para população inicial. Por enquanto, possuimos apenas uma para atualização semanal de servidores. Onde a macro se torna "pequena" e as importações são mais freqüentes.

Passo-a-passo de como utilizar a macro:

1 - Faça o download do arquivo 'Macro para Extracao de Servidores.mac', presente na pasta raiz do projeto SUAP.
2 - Edite-o, substituindo 'ZZZZ' pelo identificador de seu Órgão. Esse identificador pode ser decoberto consultando-se seu setor de recursos humanos ou seu temrminal de extração.
3 - Acesse https://acesso.serpro.gov.br/HOD10/jsp/logonID.jsp e log com seu usuário e senha
4 - Uma vez no terminal do extrator, acesso a opação EXTRACAO-SIAPE
5 - Navegue pelo terminal até a opção EXCOEXARQ -> CONSULTA/EXTRAI ARQUIVO
6 - Quando o cursor estiver posicionado para que seja digitado o NOME DO ARQUIVO, pressione o botão 'Reproduzir Macro' localizado na barra de botões do seu terminal de extração ou cliqeu em 'Ação -> Executar Macro' presente na barra de menu do seu terminal de extração
7 - Na janela 'Reproduzir macro' procure em 'Local da macro' por 'Macro para Extracao de Servidores.mac'. Caso não encontre, clique no botão 'Incluir' e aponte o diretório onde você salvou o arquivo no passo 1 desse procedimento. Quando encontrar a macro, clique em 'OK'
8 - Aguarde até que a Macro seja completamente executada. Você sabe que ela chegou ao fim, depois que o ícone de um relógio desaparecer da última linha do terminal de extração. O último arquivo a ser processdado demora um pouco, por isso, não estranhe a demora. Apenas aguarde o desaparecimento do relógio e pode deslogar logo em seguida.
9 - Acesse https://www.siapenet.gov.br/Portal/Orgao.asp e log com seu CPF e senha
10 - No menu localizado no lado esquedo da página, acesse 'Obtenção e Envio de Arquivo -> Obtenção de Arquivos -> Arquivos do Extrator'
11 - Faça o download dos 'Arquivo de Dados' EXTR1, EXTR2, EXTR3, EXTR4  e EXTR5.
12 - Extraia todos, pois eles devem vir compactados.
13 - Acesse o site administrativo do SUAP e na aplicação SUAP, selecione 'Servidores'
14 - Clique no botão 'Importar do Arquivo'
15 - Faça o upload dos 5 arquivos que foram baixados do portal SiapeNET aqui. A correspondência é:

SIAPE-SERVIDOR-EXTR I: EXTR1
SIAPE-SERVIDOR-EXTR II: EXTR2
SIAPE-SERVIDOR-EXTR III: EXTR3
SIAPE-SERVIDOR-DISPONIVEL: EXTR4
SIPE-U-RH: EXTR5

Lembrando que: A obrigatoriedade é apenas para o arquivo EXTR1, pois ele insere as informações mínimas para criação dos servidores (Matricula, CPF e Setor). Então, é possível, por exemplo, importar apenas o EXTR1. Ou apenas o EXTR1 e o EXTR5. Mas nunca apenas o EXTR5.
