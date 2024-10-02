# -*- coding: utf-8 -*-

layout_servidor_1 = dict(
    descricao='SIAPE-SERVIDOR-EXTR I',
    dica='Este arquivo insere Matrícula, Nome, Nome da Mãe, CPF, PIS, Estado Civil, Regime Jurídico, \
Situação, Dados Bancários, Afastamentos, Exclusões, Inatividades, Cargo, Classe, Nível, Padrão, Lotação.',
    total=332,
    campos={
        1: dict(nome='GR-MATRICULA', tipo='N', tamanho=12),
        2: dict(nome='IT-NO-SERVIDOR', tipo='A', tamanho=60),
        3: dict(nome='IT-NO-MAE', tipo='A', tamanho=50),
        4: dict(nome='IT-NU-CPF', tipo='N', tamanho=11),
        5: dict(nome='IT-NU-PIS-PASEP', tipo='N', tamanho=11),
        6: dict(nome='IT-CO-ESTADO-CIVIL', tipo='N', tamanho=1),
        7: dict(nome='IT-SG-REGIME-JURIDICO', tipo='A', tamanho=3),
        8: dict(nome='IT-CO-SITUACAO-SERVIDOR', tipo='N', tamanho=2),
        9: dict(nome='IT-CO-BANCO-PGTO-SERVIDOR', tipo='N', tamanho=3),
        10: dict(nome='IT-CO-AGENCIA-BANCARIA-PGTO-SERV', tipo='A', tamanho=6),
        11: dict(nome='IT-NU-CCOR-PGTO-SERVIDOR', tipo='A', tamanho=13),
        12: dict(nome='IT-CO-GRUPO-OCOR-AFASTAMENTO', tipo='N', tamanho=2),
        13: dict(nome='IT-CO-OCOR-AFASTAMENTO', tipo='N', tamanho=3),
        14: dict(nome='IT-DA-INICIO-OCOR-AFASTAMENTO', tipo='N', tamanho=8),
        15: dict(nome='IT-DA-TERMINO-OCOR-AFASTAMENTO', tipo='N', tamanho=8),
        16: dict(nome='IT-CO-DIPL-AFASTAMENTO', tipo='N', tamanho=2),
        17: dict(nome='IT-DA-PUBL-DIPL-AFASTAMENTO', tipo='N', tamanho=8),
        18: dict(nome='IT-NU-DIPL-AFASTAMENTO', tipo='A', tamanho=9),
        19: dict(nome='IT-CO-GRUPO-OCOR-EXCLUSAO', tipo='N', tamanho=2),
        20: dict(nome='IT-CO-OCOR-EXCLUSAO', tipo='N', tamanho=3),
        21: dict(nome='IT-DA-OCOR-EXCLUSAO-SERV', tipo='N', tamanho=8),
        22: dict(nome='IT-CO-DIPL-EXCLUSAO', tipo='N', tamanho=2),
        23: dict(nome='IT-DA-PUBL-DIPL-EXCLUSAO', tipo='N', tamanho=8),
        24: dict(nome='IT-NU-DIPL-EXCLUSAO', tipo='A', tamanho=9),
        25: dict(nome='IT-CO-GRUPO-OCOR-INATIVIDADE', tipo='N', tamanho=2),
        26: dict(nome='IT-CO-OCOR-INATIVIDADE', tipo='N', tamanho=3),
        27: dict(nome='IT-DA-OCOR-INATIVIDADE-SERV', tipo='N', tamanho=8),
        28: dict(nome='IT-CO-DIPL-INATIVIDADE', tipo='N', tamanho=2),
        29: dict(nome='IT-DA-PUBL-DIPL-INATIVIDADE', tipo='N', tamanho=8),
        30: dict(nome='IT-NU-DIPL-INATIVIDADE', tipo='A', tamanho=9),
        31: dict(nome='IT-CO-GRUPO-CARGO-EMPREGO', tipo='N', tamanho=3),
        32: dict(nome='IT-CO-CARGO-EMPREGO', tipo='N', tamanho=3),
        33: dict(nome='IT-CO-CLASSE', tipo='A', tamanho=1),
        34: dict(nome='IT-CO-PADRAO', tipo='A', tamanho=3),
        35: dict(nome='IT-CO-NIVEL', tipo='N', tamanho=3),
        36: dict(nome='IT-DA-OCUPACAO-CARGO-EMPREGO', tipo='N', tamanho=8),
        37: dict(nome='IT-DA-SAIDA-CARGO-EMPREGO', tipo='N', tamanho=8),
        38: dict(nome='IT-CO-UORG-LOTACAO-SERVIDOR', tipo='N', tamanho=9),
        39: dict(nome='IT-DA-LOTACAO', tipo='N', tamanho=8),
        40: dict(nome='IT-DA-EXCLUSAO-INSTITUIDOR', tipo='N', tamanho=8),
    },
)

layout_servidor_2 = dict(
    descricao='SIAPE-SERVIDOR-EXTR II',
    dica='Este arquivo insere Nascimento, Sexo, Carteria de Trabalho, Data de Cadastro no SIAPE, \
Nível Escolaridade, Ingresso no Órgão e Serviço Público, Função, Atividade, Jornada de Trabalho, Identidade, Aposentadoria.',
    total=239,
    campos={
        1: dict(nome='GR-MATRICULA', tipo='N', tamanho=12),
        2: dict(nome='IT-DA-NASCIMENTO', tipo='N', tamanho=8),
        3: dict(nome='IT-CO-SEXO', tipo='A', tamanho=1),
        4: dict(nome='IT-QT-DEPENDENTE-IR', tipo='N', tamanho=2),
        5: dict(nome='IT-NU-CARTEIRA-TRABALHO', tipo='N', tamanho=11),
        6: dict(nome='IT-NU-SERIE-CARTEIRA-TRABALHO', tipo='N', tamanho=5),
        7: dict(nome='IT-SG-UF-CTRA-SERVIDOR', tipo='A', tamanho=2),
        8: dict(nome='IT-DA-PRIMEIRO-EMPREGO', tipo='N', tamanho=8),
        9: dict(nome='IT-DA-CADASTRAMENTO-SERVIDOR', tipo='N', tamanho=8),
        10: dict(nome='IT-CO-NIVEL-ESCOLARIDADE', tipo='N', tamanho=2),
        11: dict(nome='IT-CO-GRUPO-OCOR-INGR-ORGAO', tipo='N', tamanho=2),
        12: dict(nome='IT-CO-OCOR-INGR-ORGAO', tipo='N', tamanho=3),
        13: dict(nome='IT-DA-OCOR-INGR-ORGAO-SERV', tipo='N', tamanho=8),
        14: dict(nome='IT-CO-DIPL-INGR-ORGAO', tipo='N', tamanho=2),
        15: dict(nome='IT-DA-PUBL-DIPL-INGR-ORGAO', tipo='N', tamanho=8),
        16: dict(nome='IT-NU-DIPL-INGR-ORGAO', tipo='A', tamanho=9),
        17: dict(nome='IT-CO-GRUPO-OCOR-INGR-SPUB', tipo='N', tamanho=2),
        18: dict(nome='IT-CO-OCOR-INGR-SPUB', tipo='N', tamanho=3),
        19: dict(nome='IT-DA-OCOR-INGR-SPUB-SERV', tipo='N', tamanho=8),
        20: dict(nome='IT-CO-DIPL-INGR-SPUB', tipo='N', tamanho=2),
        21: dict(nome='IT-DA-PUBL-DIPL-INGR-SPUB', tipo='N', tamanho=8),
        22: dict(nome='IT-NU-DIPL-INGR-SPUB', tipo='A', tamanho=9),
        23: dict(nome='IT-SG-FUNCAO', tipo='A', tamanho=3),
        24: dict(nome='IT-CO-NIVEL-FUNCAO', tipo='N', tamanho=4),
        25: dict(nome='IT-SG-ESCOLARIDADE-FUNCAO', tipo='A', tamanho=2),
        26: dict(nome='IT-IN-OPCAO-FUNCAO', tipo='A', tamanho=1),
        27: dict(nome='IT-DA-INGRESSO-FUNCAO', tipo='N', tamanho=8),
        28: dict(nome='IT-DA-SAIDA-FUNCAO', tipo='N', tamanho=8),
        29: dict(nome='IT-CO-UORG-FUNCAO', tipo='N', tamanho=9),
        30: dict(nome='IT-SG-NOVA-FUNCAO', tipo='A', tamanho=3),
        31: dict(nome='IT-CO-NIVEL-NOVA-FUNCAO', tipo='N', tamanho=4),
        32: dict(nome='IT-SG-ESCOLARIDADE-NOVA-FUNCAO', tipo='A', tamanho=2),
        33: dict(nome='IT-IN-OPCAO-NOVA-FUNCAO', tipo='A', tamanho=1),
        34: dict(nome='IT-DA-INGRESSO-NOVA-FUNCAO', tipo='N', tamanho=8),
        35: dict(nome='IT-DA-SAIDA-NOVA-FUNCAO', tipo='N', tamanho=8),
        36: dict(nome='IT-CO-UORG-NOVA-FUNCAO', tipo='N', tamanho=9),
        37: dict(nome='IT-CO-JORNADA-TRABALHO', tipo='N', tamanho=2),
        38: dict(nome='IT-NU-NUMERADOR-PROP', tipo='N', tamanho=2),
        39: dict(nome='IT-NU-DENOMINADOR-PROP', tipo='N', tamanho=2),
        40: dict(nome='IT-NU-PROCESSO-APOSENTADORIA', tipo='A', tamanho=30),
        41: dict(nome='IT-CO-ATIVIDADE-FUNCAO', tipo='N', tamanho=4),
        42: dict(nome='IT-CO-ATIVIDADE-NOVA-FUNCAO', tipo='N', tamanho=4),
    },
)

layout_servidor_3 = dict(
    descricao='SIAPE-SERVIDOR-EXTR III',
    dica='Este arquivo insere Código da Vaga, Título Eleitoral, Operação de Raio-X, \
Posse no Serviço Público e futuramente Titulação.',
    total=125,
    campos={
        1: dict(nome='GR-MATRICULA', tipo='N', tamanho=12),
        2: dict(nome='IT-NU-MATRICULA-ANTERIOR', tipo='N', tamanho=7),
        3: dict(nome='IT-CO-REGISTRO-GERAL', tipo='A', tamanho=14),
        4: dict(nome='IT-SG-ORGAO-EXPEDIDOR-IDEN', tipo='A', tamanho=5),
        5: dict(nome='IT-DA-EXPEDICAO-IDEN', tipo='N', tamanho=8),
        6: dict(nome='IT-SG-UF-IDEN', tipo='A', tamanho=2),
        7: dict(nome='IT-DA-OBITO', tipo='N', tamanho=8),
        8: dict(nome='NU-TITULO-ELEITOR', tipo='N', tamanho=13),
        9: dict(nome='IT-IN-OPERADOR-RAIOX', tipo='N', tamanho=1),
        10: dict(nome='IT-CO-VAGA', tipo='N', tamanho=7),
        11: dict(nome='IT-CO-GRUPO-OCOR-INGR-SPUB-POSSE', tipo='N', tamanho=2),
        12: dict(nome='IT-CO-OCOR-INGR-SPUB-POSSE', tipo='N', tamanho=3),
        13: dict(nome='IT-DA-OCOR-INGR-SPUB-POSSE', tipo='N', tamanho=8),
        14: dict(nome='IT-CO-DIPL-INGR-SPUB-POSSE', tipo='N', tamanho=2),
        15: dict(nome='IT-DA-PUBL-DIPL-INGR-SPUB-POSSE', tipo='N', tamanho=8),
        16: dict(nome='IT-NU-DIPL-INGR-SPUB-POSSE', tipo='A', tamanho=9),
        17: dict(nome='IT-CO-UORG-EXERCICIO-SERV', tipo='N', tamanho=9),
        18: dict(nome='IT-NU-SEQ-FORMACAO-RH', tipo='N', tamanho=3),
        19: dict(nome='IT-CO-TITULACAO-FORMACAO-RH', tipo='N', tamanho=2),
    },
)

layout_servidor_4 = dict(
    descricao='SIAPE-SERVIDOR-DISPONIVEL',
    dica='Este arquivo insere Endereço, Telefone, E-mail e Grupo Sangüíneo.',
    total=221,
    campos={
        1: dict(nome='GR-MATRICULA-SERV-DISPONIVEL', tipo='N', tamanho=12),
        2: dict(nome='IT-NO-LOGRADOURO', tipo='A', tamanho=40),
        3: dict(nome='IT-NO-BAIRRO', tipo='A', tamanho=25),
        4: dict(nome='IT-NO-MUNICIPIO', tipo='A', tamanho=30),
        5: dict(nome='IT-CO-CEP', tipo='N', tamanho=8),
        6: dict(nome='IT-SG-UF-SERV-DISPONIVEL', tipo='A', tamanho=2),
        7: dict(nome='IT-NU-ENDERECO', tipo='A', tamanho=6),
        8: dict(nome='IT-NU-COMPLEMENTO-ENDERECO', tipo='A', tamanho=21),
        9: dict(nome='IT-CO-PAIS-ENDERECO', tipo='N', tamanho=3),
        10: dict(nome='IT-NU-DDD-TELEFONE', tipo='A', tamanho=5),
        11: dict(nome='IT-NU-TELEFONETELEFONE', tipo='A', tamanho=9),
        12: dict(nome='IT-NU-RAMAL-TELEFONE', tipo='A', tamanho=5),
        13: dict(nome='IT-ED-CORREIO-ELETRONICO', tipo='A', tamanho=50),
        14: dict(nome='IT-SG-GRUPO-SANGUINEO', tipo='A', tamanho=2),
        15: dict(nome='IT-SG-FATOR-RH', tipo='A', tamanho=1),
    },
)

layout_servidor_5 = dict(
    descricao='SIPE-U-RH',
    dica='Este arquivo insere Naturalidade, Nome do Pai, Complementos do Título Eleitoral, \
Carteira de Habilitação, Fax e Identidade Única.',
    total=206,
    campos={
        1: dict(nome='NU-CPF-RH', tipo='N', tamanho=11),
        2: dict(nome='NO-MUNICIPIO-NASCIMENTO-RH', tipo='A', tamanho=50),
        3: dict(nome='SG-UF-NASCIMENTO-RH', tipo='A', tamanho=2),
        4: dict(nome='NO-PAI-RH', tipo='A', tamanho=50),
        5: dict(nome='SG-UF-TITULO-ELEITOR-RH', tipo='A', tamanho=2),
        6: dict(nome='NU-ZONA-ELEITORAL-RH', tipo='N', tamanho=3),
        7: dict(nome='NU-SECAO-ELEITORAL-RH', tipo='A', tamanho=4),
        8: dict(nome='DA-EMISSAO-TITULO-ELEITOR-RH', tipo='A', tamanho=8),
        9: dict(nome='NU-CART-MOTORISTA-RH', tipo='N', tamanho=10),
        10: dict(nome='NU-REGISTRO-CART-MOTORISTA-RH', tipo='N', tamanho=10),
        11: dict(nome='IN-CATEGORIA-CART-MOTORISTA-RH', tipo='A', tamanho=10),
        12: dict(nome='SG-UF-CART-MOTORISTA-RH', tipo='A', tamanho=2),
        13: dict(nome='DA-EXPEDICAO-CART-MOTORISTA-RH', tipo='A', tamanho=8),
        14: dict(nome='DA-VALIDADE-CART-MOTORISTA-RH', tipo='A', tamanho=8),
        15: dict(nome='ED-FAX-RH', tipo='A', tamanho=15),
        # O campo abaixo não é usado, mas é necessário para filtrar melhore os arquivos extraídos
        16: dict(nome='ED-SG-UF-MUNICIPIO-RH', tipo='A', tamanho=2),
        17: dict(nome='CO-IDENT-UNICA-SIAPE-RH', tipo='N', tamanho=9),
    },
)

layout_servidor_6 = dict(
    descricao='SIAPE-SERVIDOR-FERIAS',
    dica='Este arquivo insere as Férias relativas ao último ano. \
Caso deseje um histórico mais abrangente, utilize o próximo campo para executar essa tarefa.',
    total=46,
    campos={
        1: dict(nome='GR-MATRICULA-EXERCICIO-FERIAS', tipo='N', tamanho=16),
        2: dict(nome='IT-DA-INICIO-FERIAS(1)', tipo='N', tamanho=8),
        3: dict(nome='IT-QT-DIAS-FERIAS(1)', tipo='N', tamanho=2),
        4: dict(nome='IT-DA-INTERRUPCAO-FERIAS(1)', tipo='N', tamanho=8),
        5: dict(nome='IT-DA-INICIO-FERIAS-INTERROMPIDA(1)', tipo='N', tamanho=8),
        6: dict(nome='IT-QT-DIA-FERIAS-INTERROMPIDA(1)', tipo='N', tamanho=2),
    },
)


layout_servidor_7 = dict(
    descricao='SIAPE-SERVIDOR-FERIAS-HIST',
    dica='Este arquivo insere as Férias relativas a todo o histórico da Instituição. \
É demasiadamente grande e sugere-se usar apenas para popular incialmente a base de dados.',
    total=52,
    campos={
        1: dict(nome='GR-MATRICULA-EXERCICIO-FERIAS-HIST', tipo='N', tamanho=22),
        2: dict(nome='IT-DA-INICIO-FERIAS(1)', tipo='N', tamanho=8),
        3: dict(nome='IT-QT-DIAS-FERIAS(1)', tipo='N', tamanho=2),
        4: dict(nome='IT-DA-INTERRUPCAO-FERIAS(1)', tipo='N', tamanho=8),
        5: dict(nome='IT-DA-INICIO-FERIAS-INTERROMPIDA(1)', tipo='N', tamanho=8),
        6: dict(nome='IT-QT-DIA-FERIAS-INTERROMPIDA(1)', tipo='N', tamanho=2),
    },
)

layout_servidor_8 = dict(
    descricao='SIAPE-SERVIDOR-HISTORICO (Afastamentos)',
    dica='Este arquivo insere os Afastamentos relativas a todo o histórico da Instituição. \
É demasiadamente grande e sugere-se usar apenas para popular incialmente a base de dados ou quando se perceber que \
há lacunas nos relatórios de ponto.',
    total=60,
    campos={
        1: dict(nome='GR-MATRICULA-ANO-MES', tipo='N', tamanho=18),
        2: dict(nome='IT-CO-GRUPO-OCOR-AFASTAMENTO', tipo='N', tamanho=2),
        3: dict(nome='IT-CO-OCOR-AFASTAMENTO', tipo='N', tamanho=3),
        4: dict(nome='IT-DA-INICIO-OCOR-AFASTAMENTO', tipo='N', tamanho=8),
        5: dict(nome='IT-DA-TERMINO-OCOR-AFASTAMENTO', tipo='N', tamanho=8),
        6: dict(nome='IT-CO-DIPL-AFASTAMENTO', tipo='N', tamanho=2),
        7: dict(nome='IT-DA-PUBL-DIPL-AFASTAMENTO', tipo='N', tamanho=8),
        8: dict(nome='IT-NU-DIPL-AFASTAMENTO', tipo='A', tamanho=9),
    },
)

layout_setor = dict(
    descricao='SIAPE-UNIDADEORGANIZACIONAL',
    dica='Este arquivo insere Setores.',
    total=81,
    campos={
        1: dict(nome='IT-IN-STATUS-REGISTRO-TABELA', tipo='N', tamanho=1),
        2: dict(nome='GR-IDENTIFICACAO-UORG', tipo='N', tamanho=14),
        3: dict(nome='IT-NO-UNIDADE-ORGANIZACIONAL', tipo='A', tamanho=40),
        4: dict(nome='IT-SG-UNIDADE-ORGANIZACIONAL', tipo='A', tamanho=10),
        5: dict(nome='IT-CO-UORG-VINCULACAO', tipo='N', tamanho=14),
    },
)
layout_atividade = dict(
    descricao='SIAPE-ATIVIDADE',
    dica='Este arquivo insere Atividades.',
    total=37,
    campos={
        1: dict(nome='IT-IN-STATUS-REGISTRO-TABELA', tipo='N', tamanho=1),
        2: dict(nome='IT-CO-ATIVIDADE', tipo='N', tamanho=4),
        3: dict(nome='IT-NO-ATIVIDADE', tipo='A', tamanho=30),
    },
)
layout_funcao = dict(
    descricao='SIAPE-FUNCAO',
    dica='Este arquivo insere Funções.',
    total=46,
    campos={
        1: dict(nome='IT-IN-STATUS-REGISTRO-TABELA', tipo='N', tamanho=1),
        2: dict(nome='IT-SG-FUNCAO', tipo='A', tamanho=3),
        3: dict(nome='IT-NO-FUNCAO', tipo='A', tamanho=40),
    },
)
layout_cargoclasse = dict(
    descricao='SIAPE-CLASSE',
    dica='Este arquivo insere Classes de Cargos.',
    total=19,
    campos={
        1: dict(nome='IT-IN-STATUS-REGISTRO-TABELA', tipo='N', tamanho=1),
        2: dict(nome='IT-CO-CLASSE', tipo='A', tamanho=1),
        3: dict(nome='IT-NO-CLASSE', tipo='A', tamanho=15),
    },
)

layout_diplomalegal = dict(
    descricao='SIAPE-DIPLOMA-LEGAL',
    dica='Este arquivo insere Diplomas Legais.',
    total=29,
    campos={
        1: dict(nome='IT-IN-STATUS-REGISTRO-TABELA', tipo='N', tamanho=1),
        2: dict(nome='IT-CO-DIPLOMA-LEGAL', tipo='N', tamanho=2),
        3: dict(nome='IT-SG-DIPLOMA-LEGAL', tipo='A', tamanho=4),
        4: dict(nome='IT-NO-DIPLOMA-LEGAL', tipo='A', tamanho=20),
    },
)

layout_grupocargoemprego = dict(
    descricao='SIAPE-GRUPO-CARGO-EMPREGO',
    dica='Este arquivo insere Grupos de Cargos.',
    total=51,
    campos={
        1: dict(nome='IT-IN-STATUS-REGISTRO-TABELA', tipo='N', tamanho=1),
        2: dict(nome='IT-CO-GRUPO-CARGO-EMPREGO', tipo='N', tamanho=3),
        3: dict(nome='IT-SG-GRUPO-CARGO-EMPREGO', tipo='A', tamanho=5),
        4: dict(nome='IT-NO-GRUPO-CARGO-EMPREGO', tipo='A', tamanho=40),
    },
)
layout_cargoemprego = dict(
    descricao='SIAPE-CARGO-EMPREGO',
    dica='Este arquivo insere Cargos.',
    total=51,
    campos={
        1: dict(nome='IT-IN-STATUS-REGISTRO-TABELA', tipo='N', tamanho=1),
        2: dict(nome='GR-IDEN-CARGO-EMPREGO', tipo='N', tamanho=6),
        3: dict(nome='IT-NO-CARGO-EMPREGO', tipo='A', tamanho=40),
        4: dict(nome='IT-SG-ESCOLARIDADE', tipo='A', tamanho=2),
    },
)
layout_grupoocorrencia = dict(
    descricao='SIAPE-GRUPO-OCORRENCIA',
    dica='Este arquivo insere Grupos de Ocorrência.',
    total=35,
    campos={
        1: dict(nome='IT-IN-STATUS-REGISTRO-TABELA', tipo='N', tamanho=1),
        2: dict(nome='IT-CO-GRUPO-OCORRENCIA', tipo='N', tamanho=2),
        3: dict(nome='IT-NO-GRUPO-OCORRENCIA', tipo='A', tamanho=30),
    },
)
layout_jornadatrabalho = dict(
    descricao='SIAPE-JORNADA-TRABALHO',
    dica='Este arquivo insere Jornadas de Trabalho.',
    total=25,
    campos={
        1: dict(nome='IT-IN-STATUS-REGISTRO-TABELA', tipo='N', tamanho=1),
        2: dict(nome='IT-CO-JORNADA-TRABALHO', tipo='N', tamanho=2),
        3: dict(nome='IT-NO-JORNADA-TRABALHO', tipo='A', tamanho=20),
    },
)
layout_nivelescolaridade = dict(
    descricao='SIAPE-NIVEL-ESCOLARIDADE',
    dica='Este arquivo insere Npiveis de Escolaridade.',
    total=50,
    campos={
        1: dict(nome='IT-IN-STATUS-REGISTRO-TABELA', tipo='N', tamanho=1),
        2: dict(nome='IT-CO-NIVEL-ESCOLARIDADE', tipo='N', tamanho=2),
        3: dict(nome='IT-NO-NIVEL-ESCOLARIDADE', tipo='A', tamanho=45),
    },
)
layout_ocorrencia = dict(
    descricao='SIAPE-OCORRENCIA',
    dica='Este arquivo insere Ocorrências.',
    total=58,
    campos={
        1: dict(nome='IT-IN-STATUS-REGISTRO-TABELA', tipo='N', tamanho=1),
        2: dict(nome='GR-IDEN-OCORRENCIA', tipo='N', tamanho=5),
        3: dict(nome='IT-NO-OCORRENCIA', tipo='A', tamanho=50),
    },
)
layout_regimejuridico = dict(
    descricao='SIAPE-REGIME-JURIDICO',
    dica='Este arquivo insere Regimes Jurídicos.',
    total=41,
    campos={
        1: dict(nome='IT-IN-STATUS-REGISTRO-TABELA', tipo='N', tamanho=1),
        2: dict(nome='IT-SG-REGIME-JURIDICO', tipo='A', tamanho=3),
        3: dict(nome='IT-NO-REGIME-JURIDICO', tipo='A', tamanho=35),
    },
)
layout_pais = dict(
    descricao='SIAPE-PAIS',
    dica='Este arquivo insere Países.',
    total=37,
    campos={
        1: dict(nome='IT-IN-STATUS-REGISTRO-TABELA', tipo='N', tamanho=1),
        2: dict(nome='IT-CO-PAIS', tipo='A', tamanho=3),
        3: dict(nome='IT-NO-PAIS', tipo='A', tamanho=30),
        4: dict(nome='IT-IN-PAIS-EQUIPARADO', tipo='A', tamanho=1),
    },
)
layout_situacao = dict(
    descricao='SIAPE-SITUACAO-SERVIDOR',
    dica='Este arquivo insere Situações.',
    total=25,
    campos={
        1: dict(nome='IT-IN-STATUS-REGISTRO-TABELA', tipo='N', tamanho=1),
        2: dict(nome='IT-CO-SITUACAO-SERVIDOR', tipo='A', tamanho=2),
        3: dict(nome='IT-NO-SITUACAO-SERVIDOR', tipo='A', tamanho=20),
    },
)
layout_titulacao = dict(descricao='SIAPE-UF', total=30, campos={1: dict(nome='CO-FORMACAO', tipo='N', tamanho=4), 2: dict(nome='NO-FORMACAO', tipo='A', tamanho=40)})
layout_estadocivil = dict(
    descricao='SIAPE-ESTADO-CIVIL',
    dica='Este arquivo insere Estados Civis.',
    total=29,
    campos={
        1: dict(nome='IT-IN-STATUS-REGISTRO-TABELA', tipo='N', tamanho=1),
        2: dict(nome='IT-CO-ESTADO-CIVIL', tipo='N', tamanho=1),
        3: dict(nome='IT-NO-ESTADO-CIVIL', tipo='A', tamanho=25),
    },
)

layout_banco = dict(
    descricao='SIAPE-BANCOS',
    dica='Este arquivo insere Bancos.',
    total=51,
    campos={
        1: dict(nome='IT-IN-STATUS-REGISTRO-TABELA', tipo='N', tamanho=1),
        2: dict(nome='IT-CO-BANCO', tipo='N', tamanho=3),
        3: dict(nome='IT-NO-BANCO', tipo='A', tamanho=30),
        4: dict(nome='IT-SG-BANCO', tipo='A', tamanho=15),
    },
)

layout_pensionista = dict(
    descricao='SIAPE-BENEFICIARIO-PENSAO',
    dica='Este arquivo insere Pensionistas.',
    total=388,
    campos={
        1: dict(nome='IT-DA-ANO-MES-PAGAMENTO', tipo='N', tamanho=6),
        2: dict(nome='IT-NU-MATRICULA-BENEF-PENSAO', tipo='N', tamanho=8),
        3: dict(nome='IT-NO-BENEFICIARIO-PENSAO', tipo='A', tamanho=45),
        4: dict(nome='IT-DA-NASCIMENTO-BENEF-PENSAO', tipo='N', tamanho=8),
        5: dict(nome='IT-NU-CPF', tipo='N', tamanho=11),
        6: dict(nome='IT-CO-SEXO', tipo='A', tamanho=1),
        7: dict(nome='IT-CO-ESTADO-CIVIL', tipo='N', tamanho=1),
        8: dict(nome='IT-QT-DEPENDENTE-IR', tipo='N', tamanho=2),
        9: dict(nome='IT-CO-REGISTRO-GERAL', tipo='N', tamanho=14),
        10: dict(nome='IT-SG-ORGAO-EXPEDIDOR-IDEN', tipo='A', tamanho=5),
        11: dict(nome='IT-DA-EXPEDICAO-IDEN', tipo='N', tamanho=8),
        12: dict(nome='IT-SG-UF-IDEN', tipo='A', tamanho=2),
        13: dict(nome='IT-NO-LOGRADOURO', tipo='A', tamanho=40),
        14: dict(nome='IT-NO-BAIRRO', tipo='A', tamanho=25),
        15: dict(nome='IT-NO-MUNICIPIO', tipo='A', tamanho=30),
        16: dict(nome='IT-CO-CEP', tipo='N', tamanho=8),
        17: dict(nome='IT-NU-TELEFONE', tipo='N', tamanho=12),
        18: dict(nome='IT-SG-UF', tipo='A', tamanho=2),
        19: dict(nome='IT-CO-ORGAO(1)', tipo='N', tamanho=5),
        20: dict(nome='IT-NU-MATRICULA(1)', tipo='N', tamanho=7),
        21: dict(nome='IT-DA-INICIO-OCOR-PENSAO', tipo='N', tamanho=8),
        22: dict(nome='IT-DA-TERMINO-OCOR-PENSAO', tipo='N', tamanho=8),
        23: dict(nome='IT-NO-MAE', tipo='A', tamanho=50),
        24: dict(nome='IT-ED-CORREIO-ELETRONICO', tipo='A', tamanho=50),
        25: dict(nome='IT-NU-TITULO-ELEITOR', tipo='N', tamanho=13),
        26: dict(nome='IT-SG-UF-TITULO-ELEITOR', tipo='A', tamanho=2),
        27: dict(nome='IT-NU-ZONA-ELEITORAL', tipo='N', tamanho=3),
        28: dict(nome='IT-NU-SECAO-ELEITORAL', tipo='A', tamanho=4),
        29: dict(nome='IT-DA-EMISSAO-TITULO-ELEITOR', tipo='N', tamanho=8),
    },
)

layout_dependente = dict(
    descricao='SIAPE-DEPENDENTE-EXTR',
    dica='Este arquivo insere Dependentes Econômicos.',
    total=187,
    campos={
        1: dict(nome='IT-NU-DEPENDENTE', tipo='N', tamanho=8),
        2: dict(nome='IT-NO-DEPENDENTE', tipo='A', tamanho=60),
        3: dict(nome='IT-CO-SEXO', tipo='A', tamanho=1),
        4: dict(nome='GR-MATRICULA-DEPENDENCIA-SERV(1)', tipo='N', tamanho=12),
        5: dict(nome='IT-CO-GRAU-PARENTESCO(1)', tipo='N', tamanho=3),
        6: dict(nome='IT-NU-CPF', tipo='N', tamanho=11),
        7: dict(nome='IT-NO-MAE', tipo='A', tamanho=50),
        8: dict(nome='IT-DA-NASCIMENTO', tipo='N', tamanho=8),
        9: dict(nome='IT-NU-RG', tipo='A', tamanho=14),
        10: dict(nome='IT-SG-UF-RG', tipo='A', tamanho=2),
        11: dict(nome='IT-SG-ORGAO-EXPEDIDOR-RG', tipo='A', tamanho=5),
        12: dict(nome='IT-DA-EXPEDICAO-RG', tipo='N', tamanho=8),
        13: dict(nome='IT-CO-CONDICAO-DEPENDENTE(1)', tipo='N', tamanho=3),
    },
)

layout_grau_parentesco = dict(
    descricao='SIAPE-PARENTESCO',
    dica='Este arquivo insere Graus de Parentesco.',
    total=56,
    campos={
        1: dict(nome='IT-IN-STATUS-REGISTRO-TABELA', tipo='N', tamanho=1),
        2: dict(nome='IT-CO-GRAU-PARENTESCO', tipo='N', tamanho=3),
        3: dict(nome='IT-NO-GRAU-PARENTESCO', tipo='A', tamanho=50),
    },
)

layout_beneficio = dict(
    descricao='SIAPE-BENEFICIO',
    dica='Este arquivo insere Benefícios.',
    total=35,
    campos={
        1: dict(nome='IT-CO-BENEFICIO', tipo='N', tamanho=2),
        2: dict(nome='IT-NO-BENEFICIO', tipo='A', tamanho=30),
        3: dict(nome='IT-IN-STATUS-REGISTRO-TABELA', tipo='N', tamanho=1),
    },
)

layout_beneficio_dependente = dict(
    descricao='SIAPE-BENEFICIO-DEPENDENTE',
    dica="""Este arquivo associa os Benefícios aos Dependentes. 
                                    É necessário  que ambas as tabelas já tenham sido populadas.""",
    total=40,
    campos={
        1: dict(nome='GR-IDENT-BENEFICIO-DEPENDENTE', tipo='N', tamanho=22),
        2: dict(nome='IT-DA-INIC-BENEFICIO-DEPENDENTE', tipo='N', tamanho=8),
        3: dict(nome='IT-DA-TERM-BENEFICIO-DEPENDENTE', tipo='N', tamanho=8),
    },
)
