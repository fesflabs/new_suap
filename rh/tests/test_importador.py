# -*- coding: utf-8 -*-

from datetime import date

from django.apps import apps
from django.conf import settings

# from comum.importador import compactar_arquivos
from comum.models import PessoaTelefone
from djtools.utils import mask_cpf, strptime_or_default
from rh.importador import ImportadorSIAPE
from rh.tests.test_base import RHTestCase

Configuracao = apps.get_model('comum', 'configuracao')
EstadoCivil = apps.get_model('comum', 'estadocivil')
PessoaEndereco = apps.get_model('comum', 'pessoaendereco')
Municipio = apps.get_model('comum', 'municipio')

PessoaFisica = apps.get_model('rh', 'pessoafisica')
Servidor = apps.get_model('rh', 'servidor')
Setor = apps.get_model('rh', 'setor')

Atividade = apps.get_model('rh', 'atividade')
Banco = apps.get_model('rh', 'banco')
CargoClasse = apps.get_model('rh', 'cargoclasse')
CargoEmprego = apps.get_model('rh', 'cargoemprego')
DiplomaLegal = apps.get_model('rh', 'diplomalegal')

Funcao = apps.get_model('rh', 'funcao')
GrupoOcorrencia = apps.get_model('rh', 'grupoocorrencia')
JornadaTrabalho = apps.get_model('rh', 'jornadatrabalho')
NivelEscolaridade = apps.get_model('rh', 'nivelescolaridade')
Ocorrencia = apps.get_model('rh', 'ocorrencia')
RegimeJuridico = apps.get_model('rh', 'regimejuridico')
ServidorOcorrencia = apps.get_model('rh', 'servidorocorrencia')
Situacao = apps.get_model('rh', 'situacao')
SubgrupoOcorrencia = apps.get_model('rh', 'subgrupoocorrencia')
Titulacao = apps.get_model('rh', 'titulacao')


class ImportadorTest(RHTestCase):
    #    Esse metodo setUpClass faz com que rode o comando importar_siape com os arquivos das tabelas acessorias e que esses valores gravados
    #    no banco sejam usados em todos os metodos.
    def _setUp(self):
        super(ImportadorTest, self).setUp()
        # compactar_arquivos(settings.BASE_DIR + '/rh/tests/arquivos_siape_novo', settings.MEDIA_ROOT + '/rh/arquivos_siape')
        self.i = ImportadorSIAPE(log_level='WARNING')
        self.i.run()

    def criar_servidores_dict(self):
        #       Servidor 1 Situacao 1
        #       Servidor 2 Situacao 2
        #       Servidor 3 Situacao 2
        itens = [
            #                 Servidor 1
            {
                'GR-MATRICULA': '264350000010',
                'IT-NU-CPF': '00397340266',
                'IT-NO-SERVIDOR': 'NOME SOBRENOME DO TERCEIRO-NOME',
                'IT-CO-ESTADO-CIVIL': '1',
                'IT-CO-NACIONALIDADE': '1',
                'IT-SG-UF-NATURALIDADE-SERVIDOR': 'RN',
                'IT-CO-PAIS': '024',
                'IT-AN-CHEGADA-ESTRANGEIRO': '',
                'IT-NO-MAE': 'NOME DA MAE DO SERVIDOR 264350000001',
                'IT-NU-PIS-PASEP': '12345678909',
                'IT-SG-REGIME-JURIDICO': 'EST',
                'IT-CO-SITUACAO-SERVIDOR': '01',
                'IT-CO-BANCO-PGTO-SERVIDOR': '001',
                'IT-CO-AGENCIA-BANCARIA-PGTO-SERV': '03293X',
                'IT-NU-CCOR-PGTO-SERVIDOR': '123456',
                'IT-CO-GRUPO-OCOR-AFASTAMENTO': '00',
                'IT-CO-OCOR-AFASTAMENTO': '000',
                'IT-DA-INICIO-OCOR-AFASTAMENTO': '00000000',
                'IT-DA-TERMINO-OCOR-AFASTAMENTO': '00000000',
                'IT-CO-DIPL-AFASTAMENTO': '00',
                'IT-DA-PUBL-DIPL-AFASTAMENTO': '00000000',
                'IT-NU-DIPL-AFASTAMENTO': '         ',
                'IT-CO-GRUPO-OCOR-EXCLUSAO': '00',
                'IT-CO-OCOR-EXCLUSAO': '000',
                'IT-DA-OCOR-EXCLUSAO-SERV': '00000000',
                'IT-CO-DIPL-EXCLUSAO': '00',
                'IT-DA-PUBL-DIPL-EXCLUSAO': '00000000',
                'IT-NU-DIPL-EXCLUSAO': '         ',
                'IT-CO-GRUPO-OCOR-INATIVIDADE': '00',
                'IT-CO-OCOR-INATIVIDADE': '000',
                'IT-DA-OCOR-INATIVIDADE-SERV': '00000000',
                'IT-CO-DIPL-INATIVIDADE': '00',
                'IT-DA-PUBL-DIPL-INATIVIDADE': '00000000',
                'IT-NU-DIPL-INATIVIDADE': '         ',
                'IT-CO-GRUPO-CARGO-EMPREGO': '707',
                'IT-CO-CARGO-EMPREGO': '001',
                'IT-CO-CLASSE': 'D',
                'IT-CO-PADRAO': '405',
                'IT-CO-NIVEL': '000',
                'IT-DA-OCUPACAO-CARGO-EMPREGO': '20101001',
                'IT-DA-SAIDA-CARGO-EMPREGO': '20110105',
                'IT-CO-UORG-LOTACAO-SERVIDOR': '000000012',
                'IT-DA-LOTACAO': '20110921',
                'IT-DA-EXCLUSAO-INSTITUIDOR': '20100101',
            },
            #                  Servidor 2
            {
                'GR-MATRICULA': '264350000020',
                'IT-NU-CPF': '20020020000',
                'IT-NO-SERVIDOR': 'NOME SOBRENOME TERCEIRO-NOME',
                'IT-CO-ESTADO-CIVIL': '1',
                'IT-CO-NACIONALIDADE': '1',
                'IT-SG-UF-NATURALIDADE-SERVIDOR': 'RN',
                'IT-CO-PAIS': '',
                'IT-AN-CHEGADA-ESTRANGEIRO': '',
                'IT-NO-MAE': 'NOME DA MAE DO SERVIDOR 264350000001',
                'IT-NU-PIS-PASEP': '12345678909',
                'IT-SG-REGIME-JURIDICO': 'EST',
                'IT-CO-SITUACAO-SERVIDOR': '02',
                'IT-CO-BANCO-PGTO-SERVIDOR': '001',
                'IT-CO-AGENCIA-BANCARIA-PGTO-SERV': '03293X',
                'IT-NU-CCOR-PGTO-SERVIDOR': '123456',
                'IT-CO-GRUPO-OCOR-AFASTAMENTO': '00',
                'IT-CO-OCOR-AFASTAMENTO': '000',
                'IT-DA-INICIO-OCOR-AFASTAMENTO': '00000000',
                'IT-DA-TERMINO-OCOR-AFASTAMENTO': '00000000',
                'IT-CO-DIPL-AFASTAMENTO': '00',
                'IT-DA-PUBL-DIPL-AFASTAMENTO': '00000000',
                'IT-NU-DIPL-AFASTAMENTO': '000000000',
                'IT-CO-GRUPO-OCOR-EXCLUSAO': '00',
                'IT-CO-OCOR-EXCLUSAO': '000',
                'IT-DA-OCOR-EXCLUSAO-SERV': '00000000',
                'IT-CO-DIPL-EXCLUSAO': '00',
                'IT-DA-PUBL-DIPL-EXCLUSAO': '00000000',
                'IT-NU-DIPL-EXCLUSAO': '         ',
                'IT-CO-GRUPO-OCOR-INATIVIDADE': '00',
                'IT-CO-OCOR-INATIVIDADE': '000',
                'IT-DA-OCOR-INATIVIDADE-SERV': '00000000',
                'IT-CO-DIPL-INATIVIDADE': '00',
                'IT-DA-PUBL-DIPL-INATIVIDADE': '00000000',
                'IT-NU-DIPL-INATIVIDADE': '000000000',
                'IT-CO-GRUPO-CARGO-EMPREGO': '559',
                'IT-CO-CARGO-EMPREGO': '027',
                'IT-CO-CLASSE': 'D',
                'IT-CO-PADRAO': '000',
                'IT-CO-NIVEL': '234',
                'IT-DA-OCUPACAO-CARGO-EMPREGO': '20101001',
                'IT-DA-SAIDA-CARGO-EMPREGO': '20110101',
                'IT-CO-UORG-LOTACAO-SERVIDOR': '000000012',
                'IT-DA-LOTACAO': '20110921',
                'IT-DA-EXCLUSAO-INSTITUIDOR': '00000000',
            },
            #                    Atualizacao Servidor1
            {
                'GR-MATRICULA': '264350000010',  # Simula a atualizacao de um servidor
                'IT-NU-CPF': '00397340266',
                'IT-NO-SERVIDOR': 'NOME SOBRENOME DO TERCEIRO-NOME',
                'IT-CO-ESTADO-CIVIL': '1',
                'IT-CO-NACIONALIDADE': '1',
                'IT-SG-UF-NATURALIDADE-SERVIDOR': 'RN',
                'IT-CO-PAIS': '',
                'IT-AN-CHEGADA-ESTRANGEIRO': '',
                'IT-NO-MAE': 'NOME DA MAE DO SERVIDOR 264350000001',
                'IT-NU-PIS-PASEP': '12345678909',
                'IT-SG-REGIME-JURIDICO': 'EST',
                'IT-CO-SITUACAO-SERVIDOR': '02',
                'IT-CO-BANCO-PGTO-SERVIDOR': '001',
                'IT-CO-AGENCIA-BANCARIA-PGTO-SERV': '03293X',
                'IT-NU-CCOR-PGTO-SERVIDOR': '123456',
                'IT-CO-GRUPO-OCOR-AFASTAMENTO': '00',
                'IT-CO-OCOR-AFASTAMENTO': '000',
                'IT-DA-INICIO-OCOR-AFASTAMENTO': '00000000',
                'IT-DA-TERMINO-OCOR-AFASTAMENTO': '00000000',
                'IT-CO-DIPL-AFASTAMENTO': '00',
                'IT-DA-PUBL-DIPL-AFASTAMENTO': '00000000',
                'IT-NU-DIPL-AFASTAMENTO': '000000000',
                'IT-CO-GRUPO-OCOR-EXCLUSAO': '00',
                'IT-CO-OCOR-EXCLUSAO': '000',
                'IT-DA-OCOR-EXCLUSAO-SERV': '00000000',
                'IT-CO-DIPL-EXCLUSAO': '00',
                'IT-DA-PUBL-DIPL-EXCLUSAO': '00000000',
                'IT-NU-DIPL-EXCLUSAO': '000000000',
                'IT-CO-GRUPO-OCOR-INATIVIDADE': '00',
                'IT-CO-OCOR-INATIVIDADE': '000',
                'IT-DA-OCOR-INATIVIDADE-SERV': '00000000',
                'IT-CO-DIPL-INATIVIDADE': '00',
                'IT-DA-PUBL-DIPL-INATIVIDADE': '00000000',
                'IT-NU-DIPL-INATIVIDADE': '000000000',
                'IT-CO-GRUPO-CARGO-EMPREGO': '707',
                'IT-CO-CARGO-EMPREGO': '001',
                'IT-CO-CLASSE': 'D',
                'IT-CO-PADRAO': '405',
                'IT-CO-NIVEL': '000',
                'IT-DA-OCUPACAO-CARGO-EMPREGO': '20101001',
                'IT-DA-SAIDA-CARGO-EMPREGO': '20110101',
                'IT-CO-UORG-LOTACAO-SERVIDOR': '000000012',
                'IT-DA-LOTACAO': '20110921',
                'IT-DA-EXCLUSAO-INSTITUIDOR': '20100101',
            },
            #                  Servidor 3
            {
                'GR-MATRICULA': '264350000030',
                'IT-NU-CPF': '00397340298',
                'IT-NO-SERVIDOR': 'NOME SOBRENOME DO TERCEIRO-NOME',
                'IT-CO-ESTADO-CIVIL': '1',
                'IT-CO-NACIONALIDADE': '1',
                'IT-SG-UF-NATURALIDADE-SERVIDOR': 'RN',
                'IT-CO-PAIS': '',
                'IT-AN-CHEGADA-ESTRANGEIRO': '',
                'IT-NO-MAE': 'NOME DA MAE DO SERVIDOR 264350000003',
                'IT-NU-PIS-PASEP': '12345678124',
                'IT-SG-REGIME-JURIDICO': 'EST',
                'IT-CO-SITUACAO-SERVIDOR': '02',
                'IT-CO-BANCO-PGTO-SERVIDOR': '001',
                'IT-CO-AGENCIA-BANCARIA-PGTO-SERV': '032122X',
                'IT-NU-CCOR-PGTO-SERVIDOR': '123876',
                'IT-CO-GRUPO-OCOR-AFASTAMENTO': '00',
                'IT-CO-OCOR-AFASTAMENTO': '000',
                'IT-DA-INICIO-OCOR-AFASTAMENTO': '00000000',
                'IT-DA-TERMINO-OCOR-AFASTAMENTO': '00000000',
                'IT-CO-DIPL-AFASTAMENTO': '00',
                'IT-DA-PUBL-DIPL-AFASTAMENTO': '00000000',
                'IT-NU-DIPL-AFASTAMENTO': '000000000',
                'IT-CO-GRUPO-OCOR-EXCLUSAO': '00',
                'IT-CO-OCOR-EXCLUSAO': '000',
                'IT-DA-OCOR-EXCLUSAO-SERV': '00000000',
                'IT-CO-DIPL-EXCLUSAO': '00',
                'IT-DA-PUBL-DIPL-EXCLUSAO': '00000000',
                'IT-NU-DIPL-EXCLUSAO': '000000000',
                'IT-CO-GRUPO-OCOR-INATIVIDADE': '00',
                'IT-CO-OCOR-INATIVIDADE': '000',
                'IT-DA-OCOR-INATIVIDADE-SERV': '00000000',
                'IT-CO-DIPL-INATIVIDADE': '00',
                'IT-DA-PUBL-DIPL-INATIVIDADE': '00000000',
                'IT-NU-DIPL-INATIVIDADE': '000000000',
                'IT-CO-GRUPO-CARGO-EMPREGO': '063',
                'IT-CO-CARGO-EMPREGO': '001',
                'IT-CO-CLASSE': 'A',
                'IT-CO-PADRAO': 'III',
                'IT-CO-NIVEL': '000',
                'IT-DA-OCUPACAO-CARGO-EMPREGO': '00000000',
                'IT-DA-SAIDA-CARGO-EMPREGO': '00000000',
                'IT-CO-UORG-LOTACAO-SERVIDOR': '000000000',
                'IT-DA-LOTACAO': '00000000',
                'IT-DA-EXCLUSAO-INSTITUIDOR': '20100101',
            },
            #                  Servidor 4
            {
                'GR-MATRICULA': '264350000040',
                'IT-NU-CPF': '00397340211',
                'IT-NO-SERVIDOR': 'NOME SOBRENOME DO TERCEIRO-NOME',
                'IT-CO-ESTADO-CIVIL': '1',
                'IT-CO-NACIONALIDADE': '1',
                'IT-SG-UF-NATURALIDADE-SERVIDOR': 'RN',
                'IT-CO-PAIS': '',
                'IT-AN-CHEGADA-ESTRANGEIRO': '',
                'IT-NO-MAE': 'NOME DA MAE DO SERVIDOR 264350000003',
                'IT-NU-PIS-PASEP': '123456712341',
                'IT-SG-REGIME-JURIDICO': 'EST',
                'IT-CO-SITUACAO-SERVIDOR': '02',
                'IT-CO-BANCO-PGTO-SERVIDOR': '001',
                'IT-CO-AGENCIA-BANCARIA-PGTO-SERV': '015122X',
                'IT-NU-CCOR-PGTO-SERVIDOR': '121876',
                'IT-CO-GRUPO-OCOR-AFASTAMENTO': '00',
                'IT-CO-OCOR-AFASTAMENTO': '000',
                'IT-DA-INICIO-OCOR-AFASTAMENTO': '00000000',
                'IT-DA-TERMINO-OCOR-AFASTAMENTO': '00000000',
                'IT-CO-DIPL-AFASTAMENTO': '00',
                'IT-DA-PUBL-DIPL-AFASTAMENTO': '00000000',
                'IT-NU-DIPL-AFASTAMENTO': '000000000',
                'IT-CO-GRUPO-OCOR-EXCLUSAO': '00',
                'IT-CO-OCOR-EXCLUSAO': '000',
                'IT-DA-OCOR-EXCLUSAO-SERV': '00000000',
                'IT-CO-DIPL-EXCLUSAO': '00',
                'IT-DA-PUBL-DIPL-EXCLUSAO': '00000000',
                'IT-NU-DIPL-EXCLUSAO': '000000000',
                'IT-CO-GRUPO-OCOR-INATIVIDADE': '00',
                'IT-CO-OCOR-INATIVIDADE': '000',
                'IT-DA-OCOR-INATIVIDADE-SERV': '00000000',
                'IT-CO-DIPL-INATIVIDADE': '00',
                'IT-DA-PUBL-DIPL-INATIVIDADE': '00000000',
                'IT-NU-DIPL-INATIVIDADE': '000000000',
                'IT-CO-GRUPO-CARGO-EMPREGO': '000',
                'IT-CO-CARGO-EMPREGO': '000',
                'IT-CO-CLASSE': 'D',
                'IT-CO-PADRAO': '000',
                'IT-CO-NIVEL': '234',
                'IT-DA-OCUPACAO-CARGO-EMPREGO': '20101001',
                'IT-DA-SAIDA-CARGO-EMPREGO': '20110101',
                'IT-CO-UORG-LOTACAO-SERVIDOR': '000000000',
                'IT-DA-LOTACAO': '00000000',
                'IT-DA-EXCLUSAO-INSTITUIDOR': '20100101',
            },
            #                  Servidor 5 Testa exclusao
            {
                'GR-MATRICULA': '264350000050',
                'IT-NU-CPF': '0023453456',
                'IT-NO-SERVIDOR': 'NOME SOBRENOME DO TERCEIRO-NOME',
                'IT-CO-ESTADO-CIVIL': '1',
                'IT-CO-NACIONALIDADE': '1',
                'IT-SG-UF-NATURALIDADE-SERVIDOR': 'RN',
                'IT-CO-PAIS': '',
                'IT-AN-CHEGADA-ESTRANGEIRO': '',
                'IT-NO-MAE': 'NOME DA MAE DO SERVIDOR 0039123456',
                'IT-NU-PIS-PASEP': '9726543342341',
                'IT-SG-REGIME-JURIDICO': 'EST',
                'IT-CO-SITUACAO-SERVIDOR': '02',
                'IT-CO-BANCO-PGTO-SERVIDOR': '001',
                'IT-CO-AGENCIA-BANCARIA-PGTO-SERV': '0151233X',
                'IT-NU-CCOR-PGTO-SERVIDOR': '121116',
                'IT-CO-GRUPO-OCOR-AFASTAMENTO': '00',
                'IT-CO-OCOR-AFASTAMENTO': '000',
                'IT-DA-INICIO-OCOR-AFASTAMENTO': '00000000',
                'IT-DA-TERMINO-OCOR-AFASTAMENTO': '00000000',
                'IT-CO-DIPL-AFASTAMENTO': '00',
                'IT-DA-PUBL-DIPL-AFASTAMENTO': '00000000',
                'IT-NU-DIPL-AFASTAMENTO': '000000000',
                'IT-CO-GRUPO-OCOR-EXCLUSAO': '02',
                'IT-CO-OCOR-EXCLUSAO': '103',
                'IT-DA-OCOR-EXCLUSAO-SERV': '20110601',
                'IT-CO-DIPL-EXCLUSAO': '02',
                'IT-DA-PUBL-DIPL-EXCLUSAO': '20110602',
                'IT-NU-DIPL-EXCLUSAO': '0966/2011',
                'IT-CO-GRUPO-OCOR-INATIVIDADE': '00',
                'IT-CO-OCOR-INATIVIDADE': '000',
                'IT-DA-OCOR-INATIVIDADE-SERV': '00000000',
                'IT-CO-DIPL-INATIVIDADE': '00',
                'IT-DA-PUBL-DIPL-INATIVIDADE': '00000000',
                'IT-NU-DIPL-INATIVIDADE': '000000000',
                'IT-CO-GRUPO-CARGO-EMPREGO': '000',
                'IT-CO-CARGO-EMPREGO': '123',
                'IT-CO-CLASSE': 'D',
                'IT-CO-PADRAO': '000',
                'IT-CO-NIVEL': '234',
                'IT-DA-OCUPACAO-CARGO-EMPREGO': '20101001',
                'IT-DA-SAIDA-CARGO-EMPREGO': '20110101',
                'IT-CO-UORG-LOTACAO-SERVIDOR': '000000000',
                'IT-DA-LOTACAO': '00000000',
                'IT-DA-EXCLUSAO-INSTITUIDOR': '000000',
            },
            #                  Servidor 6 Testa Reativacao
            {
                'GR-MATRICULA': '264350000060',
                'IT-NU-CPF': '00234512356',
                'IT-NO-SERVIDOR': 'NOME SOBRENOME DO TERCEIRO-NOME',
                'IT-CO-ESTADO-CIVIL': '1',
                'IT-CO-NACIONALIDADE': '1',
                'IT-SG-UF-NATURALIDADE-SERVIDOR': 'RN',
                'IT-CO-PAIS': '',
                'IT-AN-CHEGADA-ESTRANGEIRO': '',
                'IT-NO-MAE': 'NOME DA MAE DO SERVIDOR 00234512356',
                'IT-NU-PIS-PASEP': '9785733342341',
                'IT-SG-REGIME-JURIDICO': 'EST',
                'IT-CO-SITUACAO-SERVIDOR': '02',
                'IT-CO-BANCO-PGTO-SERVIDOR': '001',
                'IT-CO-AGENCIA-BANCARIA-PGTO-SERV': '0151233X',
                'IT-NU-CCOR-PGTO-SERVIDOR': '121116',
                'IT-CO-GRUPO-OCOR-AFASTAMENTO': '00',
                'IT-CO-OCOR-AFASTAMENTO': '000',
                'IT-DA-INICIO-OCOR-AFASTAMENTO': '00000000',
                'IT-DA-TERMINO-OCOR-AFASTAMENTO': '00000000',
                'IT-CO-DIPL-AFASTAMENTO': '00',
                'IT-DA-PUBL-DIPL-AFASTAMENTO': '00000000',
                'IT-NU-DIPL-AFASTAMENTO': '000000000',
                'IT-CO-GRUPO-OCOR-EXCLUSAO': '00',
                'IT-CO-OCOR-EXCLUSAO': '103',
                'IT-DA-OCOR-EXCLUSAO-SERV': '20110601',
                'IT-CO-DIPL-EXCLUSAO': '02',
                'IT-DA-PUBL-DIPL-EXCLUSAO': '20110602',
                'IT-NU-DIPL-EXCLUSAO': '0966/2011',
                'IT-CO-GRUPO-OCOR-INATIVIDADE': '00',
                'IT-CO-OCOR-INATIVIDADE': '000',
                'IT-DA-OCOR-INATIVIDADE-SERV': '00000000',
                'IT-CO-DIPL-INATIVIDADE': '00',
                'IT-DA-PUBL-DIPL-INATIVIDADE': '00000000',
                'IT-NU-DIPL-INATIVIDADE': '000000000',
                'IT-CO-GRUPO-CARGO-EMPREGO': '000',
                'IT-CO-CARGO-EMPREGO': '123',
                'IT-CO-CLASSE': 'D',
                'IT-CO-PADRAO': '000',
                'IT-CO-NIVEL': '234',
                'IT-DA-OCUPACAO-CARGO-EMPREGO': '20101001',
                'IT-DA-SAIDA-CARGO-EMPREGO': '20110101',
                'IT-CO-UORG-LOTACAO-SERVIDOR': '000000000',
                'IT-DA-LOTACAO': '00000000',
                'IT-DA-EXCLUSAO-INSTITUIDOR': '000000',
            },
            #                 Servidor 7  Reativando servidor aposentado
            {
                'GR-MATRICULA': '264350000070',
                'IT-NU-CPF': '00234512357',
                'IT-NO-SERVIDOR': 'NOME SOBRENOME DO TERCEIRO-NOME',
                'IT-CO-ESTADO-CIVIL': '1',
                'IT-CO-NACIONALIDADE': '1',
                'IT-SG-UF-NATURALIDADE-SERVIDOR': 'RN',
                'IT-CO-PAIS': '',
                'IT-AN-CHEGADA-ESTRANGEIRO': '',
                'IT-NO-MAE': 'NOME DA MAE DO SERVIDOR 00234512356',
                'IT-NU-PIS-PASEP': '9785733342347',
                'IT-SG-REGIME-JURIDICO': 'EST',
                'IT-CO-SITUACAO-SERVIDOR': '02',
                'IT-CO-BANCO-PGTO-SERVIDOR': '001',
                'IT-CO-AGENCIA-BANCARIA-PGTO-SERV': '0151233X',
                'IT-NU-CCOR-PGTO-SERVIDOR': '121116',
                'IT-CO-GRUPO-OCOR-AFASTAMENTO': '00',
                'IT-CO-OCOR-AFASTAMENTO': '000',
                'IT-DA-INICIO-OCOR-AFASTAMENTO': '00000000',
                'IT-DA-TERMINO-OCOR-AFASTAMENTO': '00000000',
                'IT-CO-DIPL-AFASTAMENTO': '00',
                'IT-DA-PUBL-DIPL-AFASTAMENTO': '00000000',
                'IT-NU-DIPL-AFASTAMENTO': '000000000',
                'IT-CO-GRUPO-OCOR-EXCLUSAO': '03',
                'IT-CO-OCOR-EXCLUSAO': '186',
                'IT-DA-OCOR-EXCLUSAO-SERV': '20110601',
                'IT-CO-DIPL-EXCLUSAO': '02',
                'IT-DA-PUBL-DIPL-EXCLUSAO': '20110602',
                'IT-NU-DIPL-EXCLUSAO': '0966/2011',
                'IT-CO-GRUPO-OCOR-INATIVIDADE': '00',
                'IT-CO-OCOR-INATIVIDADE': '000',
                'IT-DA-OCOR-INATIVIDADE-SERV': '00000000',
                'IT-CO-DIPL-INATIVIDADE': '00',
                'IT-DA-PUBL-DIPL-INATIVIDADE': '00000000',
                'IT-NU-DIPL-INATIVIDADE': '000000000',
                'IT-CO-GRUPO-CARGO-EMPREGO': '000',
                'IT-CO-CARGO-EMPREGO': '123',
                'IT-CO-CLASSE': 'D',
                'IT-CO-PADRAO': '000',
                'IT-CO-NIVEL': '234',
                'IT-DA-OCUPACAO-CARGO-EMPREGO': '20101001',
                'IT-DA-SAIDA-CARGO-EMPREGO': '20110101',
                'IT-CO-UORG-LOTACAO-SERVIDOR': '000000000',
                'IT-DA-LOTACAO': '00000000',
                'IT-DA-EXCLUSAO-INSTITUIDOR': '000000',
            },
            #                 Servidor 8  AFASTAMENTO
            {
                'GR-MATRICULA': '264350000080',
                'IT-NU-CPF': '00234591827',
                'IT-NO-SERVIDOR': 'NOME SOBRENOME DO TERCEIRO-NOME',
                'IT-CO-ESTADO-CIVIL': '1',
                'IT-CO-NACIONALIDADE': '1',
                'IT-SG-UF-NATURALIDADE-SERVIDOR': 'RN',
                'IT-CO-PAIS': '',
                'IT-AN-CHEGADA-ESTRANGEIRO': '',
                'IT-NO-MAE': 'NOME DA MAE DO SERVIDOR 00234512356',
                'IT-NU-PIS-PASEP': '9123456642347',
                'IT-SG-REGIME-JURIDICO': 'EST',
                'IT-CO-SITUACAO-SERVIDOR': '02',
                'IT-CO-BANCO-PGTO-SERVIDOR': '001',
                'IT-CO-AGENCIA-BANCARIA-PGTO-SERV': '011233X',
                'IT-NU-CCOR-PGTO-SERVIDOR': '121116',
                'IT-CO-GRUPO-OCOR-AFASTAMENTO': '03',
                'IT-CO-OCOR-AFASTAMENTO': '001',
                'IT-DA-INICIO-OCOR-AFASTAMENTO': '20110701',
                'IT-DA-TERMINO-OCOR-AFASTAMENTO': '20110710',
                'IT-CO-DIPL-AFASTAMENTO': '01',
                'IT-DA-PUBL-DIPL-AFASTAMENTO': '20110630',
                'IT-NU-DIPL-AFASTAMENTO': '01/2011',
                'IT-CO-GRUPO-OCOR-EXCLUSAO': '00',
                'IT-CO-OCOR-EXCLUSAO': '000',
                'IT-DA-OCOR-EXCLUSAO-SERV': '00000000',
                'IT-CO-DIPL-EXCLUSAO': '00',
                'IT-DA-PUBL-DIPL-EXCLUSAO': '00000000',
                'IT-NU-DIPL-EXCLUSAO': '000000000',
                'IT-CO-GRUPO-OCOR-INATIVIDADE': '00',
                'IT-CO-OCOR-INATIVIDADE': '000',
                'IT-DA-OCOR-INATIVIDADE-SERV': '00000000',
                'IT-CO-DIPL-INATIVIDADE': '00',
                'IT-DA-PUBL-DIPL-INATIVIDADE': '00000000',
                'IT-NU-DIPL-INATIVIDADE': '000000000',
                'IT-CO-GRUPO-CARGO-EMPREGO': '000',
                'IT-CO-CARGO-EMPREGO': '123',
                'IT-CO-CLASSE': 'D',
                'IT-CO-PADRAO': '000',
                'IT-CO-NIVEL': '234',
                'IT-DA-OCUPACAO-CARGO-EMPREGO': '20101001',
                'IT-DA-SAIDA-CARGO-EMPREGO': '20110101',
                'IT-CO-UORG-LOTACAO-SERVIDOR': '000000000',
                'IT-DA-LOTACAO': '00000000',
                'IT-DA-EXCLUSAO-INSTITUIDOR': '000000',
            },
            #                 Servidor 9  AFASTAMENTO Diploma Legal 00
            {
                'GR-MATRICULA': '264350000090',
                'IT-NU-CPF': '0023459234',
                'IT-NO-SERVIDOR': 'NOME SOBRENOME DO TERCEIRO-NOME',
                'IT-CO-ESTADO-CIVIL': '1',
                'IT-CO-NACIONALIDADE': '1',
                'IT-SG-UF-NATURALIDADE-SERVIDOR': 'RN',
                'IT-CO-PAIS': '',
                'IT-AN-CHEGADA-ESTRANGEIRO': '',
                'IT-NO-MAE': 'NOME DA MAE DO SERVIDOR 00234512356',
                'IT-NU-PIS-PASEP': '9122222242347',
                'IT-SG-REGIME-JURIDICO': 'EST',
                'IT-CO-SITUACAO-SERVIDOR': '02',
                'IT-CO-BANCO-PGTO-SERVIDOR': '001',
                'IT-CO-AGENCIA-BANCARIA-PGTO-SERV': '099233X',
                'IT-NU-CCOR-PGTO-SERVIDOR': '199116',
                'IT-CO-GRUPO-OCOR-AFASTAMENTO': '03',
                'IT-CO-OCOR-AFASTAMENTO': '001',
                'IT-DA-INICIO-OCOR-AFASTAMENTO': '20110701',
                'IT-DA-TERMINO-OCOR-AFASTAMENTO': '20110710',
                'IT-CO-DIPL-AFASTAMENTO': '00',
                'IT-DA-PUBL-DIPL-AFASTAMENTO': '00000000',
                'IT-NU-DIPL-AFASTAMENTO': '        ',
                'IT-CO-GRUPO-OCOR-EXCLUSAO': '00',
                'IT-CO-OCOR-EXCLUSAO': '000',
                'IT-DA-OCOR-EXCLUSAO-SERV': '00000000',
                'IT-CO-DIPL-EXCLUSAO': '00',
                'IT-DA-PUBL-DIPL-EXCLUSAO': '00000000',
                'IT-NU-DIPL-EXCLUSAO': '000000000',
                'IT-CO-GRUPO-OCOR-INATIVIDADE': '00',
                'IT-CO-OCOR-INATIVIDADE': '000',
                'IT-DA-OCOR-INATIVIDADE-SERV': '00000000',
                'IT-CO-DIPL-INATIVIDADE': '00',
                'IT-DA-PUBL-DIPL-INATIVIDADE': '00000000',
                'IT-NU-DIPL-INATIVIDADE': '000000000',
                'IT-CO-GRUPO-CARGO-EMPREGO': '000',
                'IT-CO-CARGO-EMPREGO': '123',
                'IT-CO-CLASSE': 'D',
                'IT-CO-PADRAO': '000',
                'IT-CO-NIVEL': '234',
                'IT-DA-OCUPACAO-CARGO-EMPREGO': '20101001',
                'IT-DA-SAIDA-CARGO-EMPREGO': '20110101',
                'IT-CO-UORG-LOTACAO-SERVIDOR': '000000000',
                'IT-DA-LOTACAO': '00000000',
                'IT-DA-EXCLUSAO-INSTITUIDOR': '000000',
            },
            #                  Servidor 10 com mesmo cpf servidor1
            {
                'GR-MATRICULA': '264350000100',
                'IT-NU-CPF': '00397340266',
                'IT-NO-SERVIDOR': 'NOME SOBRENOME DO TERCEIRO-NOME',
                'IT-CO-ESTADO-CIVIL': '1',
                'IT-CO-NACIONALIDADE': '1',
                'IT-SG-UF-NATURALIDADE-SERVIDOR': 'RN',
                'IT-CO-PAIS': '',
                'IT-AN-CHEGADA-ESTRANGEIRO': '',
                'IT-NO-MAE': 'NOME DA MAE DO SERVIDOR',
                'IT-NU-PIS-PASEP': '12345678909',
                'IT-SG-REGIME-JURIDICO': 'EST',
                'IT-CO-SITUACAO-SERVIDOR': '01',
                'IT-CO-BANCO-PGTO-SERVIDOR': '001',
                'IT-CO-AGENCIA-BANCARIA-PGTO-SERV': '03293X',
                'IT-NU-CCOR-PGTO-SERVIDOR': '123456',
                'IT-CO-GRUPO-OCOR-AFASTAMENTO': '00',
                'IT-CO-OCOR-AFASTAMENTO': '000',
                'IT-DA-INICIO-OCOR-AFASTAMENTO': '00000000',
                'IT-DA-TERMINO-OCOR-AFASTAMENTO': '00000000',
                'IT-CO-DIPL-AFASTAMENTO': '00',
                'IT-DA-PUBL-DIPL-AFASTAMENTO': '00000000',
                'IT-NU-DIPL-AFASTAMENTO': '         ',
                'IT-CO-GRUPO-OCOR-EXCLUSAO': '00',
                'IT-CO-OCOR-EXCLUSAO': '000',
                'IT-DA-OCOR-EXCLUSAO-SERV': '00000000',
                'IT-CO-DIPL-EXCLUSAO': '00',
                'IT-DA-PUBL-DIPL-EXCLUSAO': '00000000',
                'IT-NU-DIPL-EXCLUSAO': '         ',
                'IT-CO-GRUPO-OCOR-INATIVIDADE': '00',
                'IT-CO-OCOR-INATIVIDADE': '000',
                'IT-DA-OCOR-INATIVIDADE-SERV': '00000000',
                'IT-CO-DIPL-INATIVIDADE': '00',
                'IT-DA-PUBL-DIPL-INATIVIDADE': '00000000',
                'IT-NU-DIPL-INATIVIDADE': '         ',
                'IT-CO-GRUPO-CARGO-EMPREGO': '401',
                'IT-CO-CARGO-EMPREGO': '123',
                'IT-CO-CLASSE': 'D',
                'IT-CO-PADRAO': '405',
                'IT-CO-NIVEL': '000',
                'IT-DA-OCUPACAO-CARGO-EMPREGO': '20101001',
                'IT-DA-SAIDA-CARGO-EMPREGO': '20110105',
                'IT-CO-UORG-LOTACAO-SERVIDOR': '000000012',
                'IT-DA-LOTACAO': '20110921',
                'IT-DA-EXCLUSAO-INSTITUIDOR': '20100101',
            },
        ]
        return itens

    def criar_servidores_dict2(self):
        itens = [
            {
                'GR-MATRICULA': '264350000010',
                'IT-DA-NASCIMENTO': '19820729',
                'IT-CO-SEXO': 'F',
                'IT-QT-DEPENDENTE-IR': '2',
                'IT-NU-CARTEIRA-TRABALHO': '00123456789',
                'IT-NU-SERIE-CARTEIRA-TRABALHO': '01234',
                'IT-SG-UF-CTRA-SERVIDOR': 'RN',
                'IT-DA-PRIMEIRO-EMPREGO': '20000908',
                'IT-DA-CADASTRAMENTO-SERVIDOR': '20051011',
                'IT-CO-NIVEL-ESCOLARIDADE': '13',
                'IT-CO-GRUPO-OCOR-INGR-ORGAO': '01',
                'IT-CO-OCOR-INGR-ORGAO': '100',
                'IT-DA-OCOR-INGR-ORGAO-SERV': '20061011',
                'IT-CO-DIPL-INGR-ORGAO': '00',
                'IT-DA-PUBL-DIPL-INGR-ORGAO': '20061009',
                'IT-NU-DIPL-INGR-ORGAO': 'DL 8/06  ',
                'IT-CO-GRUPO-OCOR-INGR-SPUB': '01',
                'IT-CO-OCOR-INGR-SPUB': '100',
                'IT-DA-OCOR-INGR-SPUB-SERV': '20061005',
                'IT-CO-DIPL-INGR-SPUB': '00',
                'IT-DA-PUBL-DIPL-INGR-SPUB': '20061206',
                'IT-NU-DIPL-INGR-SPUB': '  9/2006',
                'IT-SG-FUNCAO': ' CD',
                'IT-CO-NIVEL-FUNCAO': '0001',
                'IT-SG-ESCOLARIDADE-FUNCAO': 'EM',
                'IT-IN-OPCAO-FUNCAO': 'S',
                'IT-DA-INGRESSO-FUNCAO': '20101016',
                'IT-DA-SAIDA-FUNCAO': '00000000',
                'IT-CO-UORG-FUNCAO': '000000009',
                'IT-SG-NOVA-FUNCAO': '   ',
                'IT-CO-NIVEL-NOVA-FUNCAO': '0000',
                'IT-SG-ESCOLARIDADE-NOVA-FUNCAO': '  ',
                'IT-IN-OPCAO-NOVA-FUNCAO': ' ',
                'IT-DA-INGRESSO-NOVA-FUNCAO': '00000000',
                'IT-DA-SAIDA-NOVA-FUNCAO': '00000000',
                'IT-CO-UORG-NOVA-FUNCAO': '000000000',
                'IT-CO-ATIVIDADE-FUNCAO': '0001',
                'IT-CO-ATIVIDADE-NOVA-FUNCAO': '0000',
                'IT-CO-JORNADA-TRABALHO': '20',
                # 'IT-NU-NUMERADOR-PROP'          : '11',
                # 'IT-NU-DENOMINADOR-PROP'        : '12',
                'IT-NU-PROCESSO-APOSENTADORIA': '00000000181778                ',
            },
            {
                'GR-MATRICULA': '264350000020',
                'IT-DA-NASCIMENTO': '19820729',
                'IT-CO-SEXO': 'F',
                'IT-QT-DEPENDENTE-IR': '0',
                'IT-NU-CARTEIRA-TRABALHO': '00123456789',
                'IT-NU-SERIE-CARTEIRA-TRABALHO': '01234',
                'IT-SG-UF-CTRA-SERVIDOR': '  ',
                'IT-DA-PRIMEIRO-EMPREGO': '20000908',
                'IT-DA-CADASTRAMENTO-SERVIDOR': '20051011',
                'IT-CO-NIVEL-ESCOLARIDADE': '14',
                'IT-CO-GRUPO-OCOR-INGR-ORGAO': '00',
                'IT-CO-OCOR-INGR-ORGAO': '000',
                'IT-DA-OCOR-INGR-ORGAO-SERV': '00000000',
                'IT-CO-DIPL-INGR-ORGAO': '00',
                'IT-DA-PUBL-DIPL-INGR-ORGAO': '00000000',
                'IT-NU-DIPL-INGR-ORGAO': '         ',
                'IT-CO-GRUPO-OCOR-INGR-SPUB': '00',
                'IT-CO-OCOR-INGR-SPUB': '000',
                'IT-DA-OCOR-INGR-SPUB-SERV': '00000000',
                'IT-CO-DIPL-INGR-SPUB': '00',
                'IT-DA-PUBL-DIPL-INGR-SPUB': '00000000',
                'IT-NU-DIPL-INGR-SPUB': '         ',
                'IT-SG-FUNCAO': ' CD',
                'IT-CO-NIVEL-FUNCAO': '0001',
                'IT-SG-ESCOLARIDADE-FUNCAO': 'EM',
                'IT-IN-OPCAO-FUNCAO': 'S',
                'IT-DA-INGRESSO-FUNCAO': '20101016',
                'IT-DA-SAIDA-FUNCAO': '00000000',
                'IT-CO-UORG-FUNCAO': '000000009',
                'IT-SG-NOVA-FUNCAO': '   ',
                'IT-CO-NIVEL-NOVA-FUNCAO': '0000',
                'IT-SG-ESCOLARIDADE-NOVA-FUNCAO': '  ',
                'IT-IN-OPCAO-NOVA-FUNCAO': ' ',
                'IT-DA-INGRESSO-NOVA-FUNCAO': '00000000',
                'IT-DA-SAIDA-NOVA-FUNCAO': '00000000',
                'IT-CO-UORG-NOVA-FUNCAO': '000000000',
                'IT-CO-ATIVIDADE-FUNCAO': '0001',
                'IT-CO-ATIVIDADE-NOVA-FUNCAO': '0000',
                'IT-CO-JORNADA-TRABALHO': '30',
                # 'IT-NU-NUMERADOR-PROP'          : '00',
                # 'IT-NU-DENOMINADOR-PROP'        : '00',
                'IT-NU-PROCESSO-APOSENTADORIA': '00000000000000               ',
            },
        ]
        return itens

    def criar_servidores_dict3(self):
        itens = [
            {
                'GR-MATRICULA': '261350000010',
                'IT-NU-MATRICULA-ANTERIOR': '1041781',
                'IT-CO-REGISTRO-GERAL': '332653        ',
                'IT-SG-ORGAO-EXPEDIDOR-IDEN': 'SSP  ',
                'IT-DA-EXPEDICAO-IDEN': '19750113',
                'IT-SG-UF-IDEN': 'RN',
                'IT-DA-OBITO': '20110301',
                'IT-NU-TITULO-ELEITOR': '0024783851610',
                'IT-IN-OPERADOR-RAIOX': '1',
                'IT-CO-VAGA': '0313710',
                'IT-CO-GRUPO-OCOR-INGR-SPUB-POSSE': '00',
                'IT-CO-OCOR-INGR-SPUB-POSSE': '000',
                'IT-DA-OCOR-INGR-SPUB-POSSE': '00000000',
                'IT-CO-DIPL-INGR-SPUB-POSSE': '00',
                'IT-DA-PUBL-DIPL-INGR-SPUB-POSSE': '00000000',
                'IT-NU-DIPL-INGR-SPUB-POSSE': '         ',
                'IT-CO-UORG-EXERCICIO-SERV': '000000030',
                'IT-CO-TITULACAO-FORMACAO-RH': '23',
            },
            {
                'GR-MATRICULA': '261350000020',
                'IT-NU-MATRICULA-ANTERIOR': '2041782',
                'IT-CO-REGISTRO-GERAL': '432654        ',
                'IT-SG-ORGAO-EXPEDIDOR-IDEN': 'ITEP ',
                'IT-DA-EXPEDICAO-IDEN': '19850110',
                'IT-SG-UF-IDEN': 'RJ',
                'IT-DA-OBITO': '00000000',
                'IT-NU-TITULO-ELEITOR': '0034783851613',
                'IT-IN-OPERADOR-RAIOX': '0',
                'IT-CO-VAGA': '2313712',
                'IT-CO-GRUPO-OCOR-INGR-SPUB-POSSE': '00',
                'IT-CO-OCOR-INGR-SPUB-POSSE': '000',
                'IT-DA-OCOR-INGR-SPUB-POSSE': '00000000',
                'IT-CO-DIPL-INGR-SPUB-POSSE': '00',
                'IT-DA-PUBL-DIPL-INGR-SPUB-POSSE': '00000000',
                'IT-NU-DIPL-INGR-SPUB-POSSE': '         ',
                'IT-CO-UORG-EXERCICIO-SERV': '000000035',
                'IT-CO-TITULACAO-FORMACAO-RH': '25',
            },
            {
                'GR-MATRICULA': '261350000030',
                'IT-NU-MATRICULA-ANTERIOR': '0000000',
                'IT-CO-REGISTRO-GERAL': '              ',
                'IT-SG-ORGAO-EXPEDIDOR-IDEN': '     ',
                'IT-DA-EXPEDICAO-IDEN': '00000000',
                'IT-SG-UF-IDEN': '  ',
                'IT-DA-OBITO': '00000000',
                'IT-NU-TITULO-ELEITOR': '0000000000000',
                'IT-IN-OPERADOR-RAIOX': '0',
                'IT-CO-VAGA': '0000000',
                'IT-CO-GRUPO-OCOR-INGR-SPUB-POSSE': '00',
                'IT-CO-OCOR-INGR-SPUB-POSSE': '000',
                'IT-DA-OCOR-INGR-SPUB-POSSE': '00000000',
                'IT-CO-DIPL-INGR-SPUB-POSSE': '00',
                'IT-DA-PUBL-DIPL-INGR-SPUB-POSSE': '00000000',
                'IT-NU-DIPL-INGR-SPUB-POSSE': '         ',
                'IT-CO-UORG-EXERCICIO-SERV': '000000000',
                'IT-CO-TITULACAO-FORMACAO-RH': '00',
            },
        ]
        return itens

    def criar_servidores_dict4(self):
        itens = [
            {
                'GR-MATRICULA-SERV-DISPONIVEL': '261350000010',
                'IT-ED-CORREIO-ELETRONICO': '100@EMAIL.SECUNDARIO',
                'IT-SG-GRUPO-SANGUINEO': 'AB',
                'IT-SG-FATOR-RH': '+',
                'IT-NO-LOGRADOURO': '',
                'IT-NO-BAIRRO': '',
                'IT-NO-MUNICIPIO': '',
                'IT-CO-CEP': '',
                'IT-SG-UF-SERV-DISPONIVEL': '',
                'IT-NU-ENDERECO': '',
                'IT-CO-COR-ORIGEM-ETNICA': '01',
                'IT-CO-GRUPO-DEFICIENCIA-FISICA': '00',
                'IT-CO-DEFICIENCIA-FISICA': '000',
                'IT-NU-COMPLEMENTO-ENDERECO': '',
                'IT-NU-DDD-TELEFONE': '',
                'IT-NU-TELEFONE': '',
                'IT-NU-RAMAL-TELEFONE': '',
                'IT-NU-DDD-TELEFONE-MOVEL': '',
                'IT-NU-TELEFONE-MOVEL': '',
            },
            {
                'GR-MATRICULA-SERV-DISPONIVEL': '261350000020',
                'IT-ED-CORREIO-ELETRONICO': '',
                'IT-SG-GRUPO-SANGUINEO': 'NI',
                'IT-SG-FATOR-RH': '',
                'IT-NO-LOGRADOURO': '',
                'IT-NO-BAIRRO': '',
                'IT-NO-MUNICIPIO': '',
                'IT-CO-CEP': '',
                'IT-SG-UF-SERV-DISPONIVEL': '',
                'IT-NU-ENDERECO': '',
                'IT-CO-COR-ORIGEM-ETNICA': '01',
                'IT-CO-GRUPO-DEFICIENCIA-FISICA': '00',
                'IT-CO-DEFICIENCIA-FISICA': '000',
                'IT-NU-COMPLEMENTO-ENDERECO': '',
                'IT-NU-DDD-TELEFONE': '',
                'IT-NU-TELEFONE': '',
                'IT-NU-RAMAL-TELEFONE': '',
                'IT-NU-DDD-TELEFONE-MOVEL': '',
                'IT-NU-TELEFONE-MOVEL': '',
            },
            {
                'GR-MATRICULA-SERV-DISPONIVEL': '261350000030',
                'IT-ED-CORREIO-ELETRONICO': '',
                'IT-SG-GRUPO-SANGUINEO': '',
                'IT-SG-FATOR-RH': '',
                'IT-NO-LOGRADOURO': '',
                'IT-NO-BAIRRO': '',
                'IT-NO-MUNICIPIO': '',
                'IT-CO-CEP': '',
                'IT-SG-UF-SERV-DISPONIVEL': '',
                'IT-NU-ENDERECO': '',
                'IT-CO-COR-ORIGEM-ETNICA': '01',
                'IT-CO-GRUPO-DEFICIENCIA-FISICA': '00',
                'IT-CO-DEFICIENCIA-FISICA': '000',
                'IT-NU-COMPLEMENTO-ENDERECO': '',
                'IT-NU-DDD-TELEFONE': '',
                'IT-NU-TELEFONE': '',
                'IT-NU-RAMAL-TELEFONE': '',
                'IT-NU-DDD-TELEFONE-MOVEL': '',
                'IT-NU-TELEFONE-MOVEL': '',
            },
        ]
        return itens

    def criar_servidores_dict5(self):
        itens = [
            {
                'NU-CPF-RH': '00397340266',
                'NO-MUNICIPIO-NASCIMENTO-RH': 'MUNICIPIO DE NASCIMENTO',
                'SG-UF-NASCIMENTO-RH': 'RN',
                'NO-PAI-RH': 'PAI DO SERVIDOR 100',
                'SG-UF-TITULO-ELEITOR-RH': 'RN',
                'NU-ZONA-ELEITORAL-RH': '001',
                'NU-SECAO-ELEITORAL-RH': '0123',
                'DA-EMISSAO-TITULO-ELEITOR-RH': '19900203',
                'NU-CART-MOTORISTA-RH': '0319900203',
                'NU-REGISTRO-CART-MOTORISTA-RH': '0101230123',
                'IN-CATEGORIA-CART-MOTORISTA-RH': '3973402661',
                'SG-UF-CART-MOTORISTA-RH': 'RN',
                'DA-EXPEDICAO-CART-MOTORISTA-RH': '19990304',
                'DA-VALIDADE-CART-MOTORISTA-RH': '20120304',
                'ED-FAX-RH': '0008489860460',
                'ED-SG-UF-MUNICIPIO-RH': 'RN',  # campo não importado
                'CO-IDENT-UNICA-SIAPE-RH': '000001001',
            },
            {
                'NU-CPF-RH': '20020020000',
                'NO-MUNICIPIO-NASCIMENTO-RH': '',
                'SG-UF-NASCIMENTO-RH': '',
                'NO-PAI-RH': '',
                'SG-UF-TITULO-ELEITOR-RH': '',
                'NU-ZONA-ELEITORAL-RH': '',
                'NU-SECAO-ELEITORAL-RH': '',
                'DA-EMISSAO-TITULO-ELEITOR-RH': '',
                'NU-CART-MOTORISTA-RH': '',
                'NU-REGISTRO-CART-MOTORISTA-RH': '',
                'IN-CATEGORIA-CART-MOTORISTA-RH': '',
                'SG-UF-CART-MOTORISTA-RH': '',
                'DA-EXPEDICAO-CART-MOTORISTA-RH': '',
                'DA-VALIDADE-CART-MOTORISTA-RH': '',
                'ED-FAX-RH': '',
                'ED-SG-UF-MUNICIPIO-RH': '',  # campo não importado
                'CO-IDENT-UNICA-SIAPE-RH': '',
            },
            {
                'NU-CPF-RH': '00397340298',
                'NO-MUNICIPIO-NASCIMENTO-RH': '',
                'SG-UF-NASCIMENTO-RH': '',
                'NO-PAI-RH': '',
                'SG-UF-TITULO-ELEITOR-RH': '',
                'NU-ZONA-ELEITORAL-RH': '',
                'NU-SECAO-ELEITORAL-RH': '',
                'DA-EMISSAO-TITULO-ELEITOR-RH': '',
                'NU-CART-MOTORISTA-RH': '',
                'NU-REGISTRO-CART-MOTORISTA-RH': '',
                'IN-CATEGORIA-CART-MOTORISTA-RH': '',
                'SG-UF-CART-MOTORISTA-RH': '',
                'DA-EXPEDICAO-CART-MOTORISTA-RH': '',
                'DA-VALIDADE-CART-MOTORISTA-RH': '',
                'ED-FAX-RH': '',
                'ED-SG-UF-MUNICIPIO-RH': '',  # campo não importado
                'CO-IDENT-UNICA-SIAPE-RH': '',
            },
        ]
        return itens

    def criar_ferias_servidor_dict(self):
        itens = [
            {
                'IT-IN-QUITACAO-FERIAS': '0',
                'GR-MATR-EXERCICIO-FERIAS-HIST': '2643500000102013201301',
                'IT-DA-INICIO-FERIAS(1)': '20130101',
                'IT-DA-INICIO-FERIAS(2)': '00000000',
                'IT-DA-INICIO-FERIAS(3)': '00000000',
                'IT-QT-DIAS-FERIAS(1)': '30',
                'IT-QT-DIAS-FERIAS(2)': '00',
                'IT-QT-DIAS-FERIAS(3)': '00',
                'IT-IN-ABONO-PECUNIARIO-FERIAS(1)': '0',
                'IT-IN-ADIANTAMENTO-FERIAS(1)': '0',
                'IT-IN-ADIANTAMENTO-FERIAS(2)': '0',
                'IT-IN-ADIANTAMENTO-FERIAS(3)': '0',
                'IT-IN-ADIANTAMENTO-GRAT-NATALINA(1)': '1',
                'IT-IN-ADIANTAMENTO-GRAT-NATALINA(2)': '1',
                'IT-IN-ADIANTAMENTO-GRAT-NATALINA(3)': '1',
                'IT-IN-CANCELAMENTO-FERIAS(1)': '0',
                'IT-IN-EXCLUSAO-FERIAS': '0',
                'IT-DA-INTERRUPCAO-FERIAS(1)': '00000000',
                'IT-DA-INTERRUPCAO-FERIAS(2)': '00000000',
                'IT-DA-INTERRUPCAO-FERIAS(3)': '00000000',
                'IT-DA-INICIO-FERIAS-INTERROMPIDA(1)': '00000000',
                'IT-DA-INICIO-FERIAS-INTERROMPIDA(2)': '00000000',
                'IT-DA-INICIO-FERIAS-INTERROMPIDA(3)': '00000000',
                'IT-QT-DIA-FERIAS-INTERROMPIDA(1)': '00',
                'IT-QT-DIA-FERIAS-INTERROMPIDA(2)': '00',
                'IT-QT-DIA-FERIAS-INTERROMPIDA(3)': '00',
            },
            {
                'IT-IN-QUITACAO-FERIAS': '1',
                'GR-MATR-EXERCICIO-FERIAS-HIST': '2643500000102013201301',
                'IT-DA-INICIO-FERIAS(1)': '20130101',
                'IT-DA-INICIO-FERIAS(2)': '00000000',
                'IT-DA-INICIO-FERIAS(3)': '00000000',
                'IT-QT-DIAS-FERIAS(1)': '30',
                'IT-QT-DIAS-FERIAS(2)': '00',
                'IT-QT-DIAS-FERIAS(3)': '00',
                'IT-IN-ABONO-PECUNIARIO-FERIAS(1)': '0',
                'IT-IN-ADIANTAMENTO-FERIAS(1)': '0',
                'IT-IN-ADIANTAMENTO-FERIAS(2)': '0',
                'IT-IN-ADIANTAMENTO-FERIAS(3)': '0',
                'IT-IN-ADIANTAMENTO-GRAT-NATALINA(1)': '1',
                'IT-IN-ADIANTAMENTO-GRAT-NATALINA(2)': '1',
                'IT-IN-ADIANTAMENTO-GRAT-NATALINA(3)': '1',
                'IT-IN-CANCELAMENTO-FERIAS(1)': '0',
                'IT-IN-EXCLUSAO-FERIAS': '0',
                'IT-DA-INTERRUPCAO-FERIAS(1)': '00000000',
                'IT-DA-INTERRUPCAO-FERIAS(2)': '00000000',
                'IT-DA-INTERRUPCAO-FERIAS(3)': '00000000',
                'IT-DA-INICIO-FERIAS-INTERROMPIDA(1)': '00000000',
                'IT-DA-INICIO-FERIAS-INTERROMPIDA(2)': '00000000',
                'IT-DA-INICIO-FERIAS-INTERROMPIDA(3)': '00000000',
                'IT-QT-DIA-FERIAS-INTERROMPIDA(1)': '00',
                'IT-QT-DIA-FERIAS-INTERROMPIDA(2)': '00',
                'IT-QT-DIA-FERIAS-INTERROMPIDA(3)': '00',
            },
            {
                'IT-IN-QUITACAO-FERIAS': '0',
                'GR-MATR-EXERCICIO-FERIAS-HIST': '2643500000202013201301',
                'IT-DA-INICIO-FERIAS(1)': '20130101',
                'IT-DA-INICIO-FERIAS(2)': '00000000',
                'IT-DA-INICIO-FERIAS(3)': '00000000',
                'IT-QT-DIAS-FERIAS(1)': '30',
                'IT-QT-DIAS-FERIAS(2)': '00',
                'IT-QT-DIAS-FERIAS(3)': '00',
                'IT-IN-ABONO-PECUNIARIO-FERIAS(1)': '0',
                'IT-IN-ADIANTAMENTO-FERIAS(1)': '0',
                'IT-IN-ADIANTAMENTO-FERIAS(2)': '0',
                'IT-IN-ADIANTAMENTO-FERIAS(3)': '0',
                'IT-IN-ADIANTAMENTO-GRAT-NATALINA(1)': '1',
                'IT-IN-ADIANTAMENTO-GRAT-NATALINA(2)': '0',
                'IT-IN-ADIANTAMENTO-GRAT-NATALINA(3)': '0',
                'IT-IN-CANCELAMENTO-FERIAS(1)': '0',
                'IT-IN-EXCLUSAO-FERIAS': '0',
                'IT-DA-INTERRUPCAO-FERIAS(1)': '00000000',
                'IT-DA-INTERRUPCAO-FERIAS(2)': '00000000',
                'IT-DA-INTERRUPCAO-FERIAS(3)': '00000000',
                'IT-DA-INICIO-FERIAS-INTERROMPIDA(1)': '00000000',
                'IT-DA-INICIO-FERIAS-INTERROMPIDA(2)': '00000000',
                'IT-DA-INICIO-FERIAS-INTERROMPIDA(3)': '00000000',
                'IT-QT-DIA-FERIAS-INTERROMPIDA(1)': '00',
                'IT-QT-DIA-FERIAS-INTERROMPIDA(2)': '00',
                'IT-QT-DIA-FERIAS-INTERROMPIDA(3)': '00',
            },
        ]
        return itens

    def _test_importar_servidor1(self):
        """ Testa a função importar_servidor1() com valores simples
            Testamos aqui somente os campos que estão diretamente relacionados 
            ao objeto Servidor, que não precisam criar outro objeto (como ocorrencias). 
            Para testar casos em que devem ser criados/manipulados outros objetos, 
            temos teste mais especializados
        """
        itens = self.criar_servidores_dict()

        self.i.importar_servidor1(itens)
        #       Verifica se a inportacao do servidor1 foram efetuados pelo arquivo
        servidor1, created = Servidor.objects.get_or_create(matricula='10')
        self.assertFalse(created)
        #       Verifica se foi criado o username na importacao e se esse username == matricula dele
        self.assertEqual(servidor1.username, servidor1.matricula)
        #       Dados do modelo Pessoa e PessoaFisica
        self.assertEqual(servidor1.sistema_origem, 'SIAPE')
        self.assertEqual(servidor1.excluido, False)
        self.assertEqual(servidor1.nome.upper(), itens[0]['IT-NO-SERVIDOR'])

        self.assertEqual(servidor1.nome_usual, 'Nome Terceiro-nome')

        self.assertEqual(servidor1.cpf, mask_cpf(itens[0]['IT-NU-CPF']))
        self.assertEqual(servidor1.pis_pasep, itens[0]['IT-NU-PIS-PASEP'])
        self.assertEqual(servidor1.estado_civil, EstadoCivil.objects.get(codigo_siape='1'))
        #        Dados Bancarios
        self.assertEqual(servidor1.pagto_banco, Banco.objects.get(codigo='001'))
        self.assertEqual(servidor1.pagto_agencia, itens[0]['IT-CO-AGENCIA-BANCARIA-PGTO-SERV'])
        self.assertEqual(servidor1.pagto_ccor, itens[0]['IT-NU-CCOR-PGTO-SERVIDOR'])
        #        Dados do modelo Servidor
        self.assertEqual(servidor1.matricula, '10')
        self.assertEqual(servidor1.identificacao_unica_siape, 'Novo')
        self.assertEqual(servidor1.regime_juridico, RegimeJuridico.objects.get(sigla='EST'))
        self.assertEqual(servidor1.situacao, Situacao.objects.get(codigo='02'))
        self.assertEqual(servidor1.data_exclusao_instituidor, strptime_or_default(itens[0]['IT-DA-EXCLUSAO-INSTITUIDOR'], '%Y%m%d').date())
        self.assertEqual(servidor1.cargo_emprego_data_saida, date(2011, 1, 1))
        #       Testando dados do item[1]
        servidor2, created = Servidor.objects.get_or_create(matricula='20')
        self.assertEqual(servidor2.identificacao_unica_siape, 'Novo')
        self.assertEqual(servidor2.situacao, Situacao.objects.get(codigo='02'))
        self.assertEqual(servidor2.regime_juridico, RegimeJuridico.objects.get(sigla='EST'))
        self.assertEqual(servidor2.data_exclusao_instituidor, None)
        self.assertEqual(servidor2.username, '20')

        #        Teste Lotacao: A lotacao agora não tem um metodo proprio para importar... ela faz parte do importar_servidor1. Por isso
        #        Verificamos se o servidor1 tem lotacao e depois se o setor dele esta vazio pois servidores novos com arvore SUAP deverao ter setor vazio
        self.assertEqual(servidor1.setor_lotacao, Setor.todos.get(codigo=itens[0]['IT-CO-UORG-LOTACAO-SERVIDOR']))
        self.assertEqual(servidor1.setor_lotacao_data_ocupacao, date(2011, 9, 21))
        # Regra: Novos servidores deverão ter o setor vazio
        self.assertEqual(servidor1.setor, None)
        #        Cria um setor para o servidor e manda salvar para ver se o importador apaga... o comportamento esperado eh nao apagar o setor.
        self.assertEqual(servidor2.setor, None)
        servidor2.setor = servidor2.setor_lotacao
        servidor2.save()
        self.i.importar_servidor1(itens)
        servidor2, created = Servidor.objects.get_or_create(matricula='20')
        self.assertNotEqual(servidor2.setor, None)

        #       TESTE CARGO EMPREGO
        #       Servidor com padrao
        self.assertEqual(servidor1.cargo_emprego, CargoEmprego.objects.get(codigo=itens[0]['IT-CO-GRUPO-CARGO-EMPREGO'] + itens[0]['IT-CO-CARGO-EMPREGO']))
        self.assertEqual(servidor1.cargo_classe, CargoClasse.objects.get(codigo=itens[0]['IT-CO-CLASSE']))
        self.assertEqual(servidor1.nivel_padrao, itens[0]['IT-CO-PADRAO'])

        self.assertEqual(servidor1.cargo_emprego_data_ocupacao, strptime_or_default(itens[0]['IT-DA-OCUPACAO-CARGO-EMPREGO'], '%Y%m%d').date())
        self.assertEqual(servidor1.cargo_emprego_data_saida, strptime_or_default(itens[2]['IT-DA-SAIDA-CARGO-EMPREGO'], '%Y%m%d').date())
        #       Servidor Com nivel

        servidor3, created = Servidor.objects.get_or_create(matricula='30')
        self.assertFalse(created)
        self.assertEqual(servidor3.nivel_padrao, '000')

        servidor4, created = Servidor.objects.get_or_create(matricula='40')
        self.assertEqual(servidor4.nivel_padrao, '000')
        self.assertEqual(servidor4.cargo_emprego, None)

        #        TESTA EXCLUSAO
        # Testa se o subgrupo de ocorrencia EXCLUSAO foi criado
        servidor5, created = Servidor.objects.get_or_create(matricula='50')
        self.assertFalse(created)
        self.assertEqual(SubgrupoOcorrencia.objects.filter(descricao='EXCLUSAO').count(), 1)
        # Recuperando a ocorrencia de exclusao do servidor
        so = ServidorOcorrencia.objects.get(
            servidor=servidor5,
            ocorrencia=Ocorrencia.objects.get(codigo=itens[5]['IT-CO-GRUPO-OCOR-EXCLUSAO'] + itens[5]['IT-CO-OCOR-EXCLUSAO']),
            diploma_legal=DiplomaLegal.objects.get(codigo=itens[5]['IT-CO-DIPL-EXCLUSAO']),
            data=strptime_or_default(itens[5]['IT-DA-OCOR-EXCLUSAO-SERV'], '%Y%m%d'),
            diploma_legal_num=itens[5]['IT-NU-DIPL-EXCLUSAO'],
            diploma_legal_data=strptime_or_default(itens[5]['IT-DA-PUBL-DIPL-EXCLUSAO'], '%Y%m%d'),
        )
        self.assertEqual(so.subgrupo.descricao, 'EXCLUSAO')
        servidor = Servidor.objects.get(matricula='50')
        self.assertTrue(servidor.excluido)

        # Testando servidor que volta para a ativa
        servidor6, created = Servidor.objects.get_or_create(matricula='60')
        #       Simula como se o servidor tivesse excluido
        servidor6.excluido = True
        servidor6.save()
        self.i.importar_servidor1(itens)
        #        Testando servidor de volta a ativa
        servidor6, created = Servidor.objects.get_or_create(matricula='60')
        self.assertFalse(servidor6.excluido)

        #     "Reativando" um servidor aposentado
        servidor7, created = Servidor.objects.get_or_create(matricula='70')
        self.assertTrue(servidor7.excluido)
        falta_de_recadastramento = servidor7.servidorocorrencia_set.all()[0]
        self.assertNotEqual(falta_de_recadastramento, None)
        #        AFASTAMENTO
        # Testando a inclusao de um novo afastamento
        servidor8, created = Servidor.objects.get_or_create(matricula='80')
        self.assertFalse(created)
        so_ant = ServidorOcorrencia.objects.get(
            servidor=servidor8,
            ocorrencia=Ocorrencia.objects.get(codigo=itens[8]['IT-CO-GRUPO-OCOR-AFASTAMENTO'] + itens[8]['IT-CO-OCOR-AFASTAMENTO']),
            data=strptime_or_default(itens[8]['IT-DA-INICIO-OCOR-AFASTAMENTO'], '%Y%m%d'),
            data_termino=strptime_or_default(itens[8]['IT-DA-TERMINO-OCOR-AFASTAMENTO'], '%Y%m%d'),
            diploma_legal=DiplomaLegal.objects.get(codigo=itens[8]['IT-CO-DIPL-AFASTAMENTO']),
            diploma_legal_data=strptime_or_default(itens[8]['IT-DA-PUBL-DIPL-AFASTAMENTO'], '%Y%m%d'),
            diploma_legal_num=itens[8]['IT-NU-DIPL-AFASTAMENTO'],
        )
        self.assertNotEqual(so, None)
        itens[8]['IT-DA-TERMINO-OCOR-AFASTAMENTO'] = '20110710'
        itens[8]['IT-CO-DIPL-AFASTAMENTO'] = '02'
        itens[8]['IT-DA-PUBL-DIPL-AFASTAMENTO'] = '20110701'
        itens[8]['IT-NU-DIPL-AFASTAMENTO'] = '02/2011'
        # Testando a alteração de uma afastamento
        self.i.importar_servidor1(itens)
        servidor8, created = Servidor.objects.get_or_create(matricula='80')
        so_novo = ServidorOcorrencia.objects.get(
            servidor=servidor8,
            ocorrencia=Ocorrencia.objects.get(codigo=itens[8]['IT-CO-GRUPO-OCOR-AFASTAMENTO'] + itens[8]['IT-CO-OCOR-AFASTAMENTO']),
            data=strptime_or_default(itens[8]['IT-DA-INICIO-OCOR-AFASTAMENTO'], '%Y%m%d'),
            data_termino=strptime_or_default(itens[8]['IT-DA-TERMINO-OCOR-AFASTAMENTO'], '%Y%m%d'),
            diploma_legal=DiplomaLegal.objects.get(codigo=itens[8]['IT-CO-DIPL-AFASTAMENTO']),
            diploma_legal_data=strptime_or_default(itens[8]['IT-DA-PUBL-DIPL-AFASTAMENTO'], '%Y%m%d'),
            diploma_legal_num=itens[8]['IT-NU-DIPL-AFASTAMENTO'],
        )
        self.assertNotEqual(so_ant.diploma_legal_num, so_novo.diploma_legal_num)

        servidor9, created = Servidor.objects.get_or_create(matricula='90')
        so_sem_dipl = ServidorOcorrencia.objects.get(
            servidor=servidor9,
            ocorrencia=Ocorrencia.objects.get(codigo=itens[9]['IT-CO-GRUPO-OCOR-AFASTAMENTO'] + itens[9]['IT-CO-OCOR-AFASTAMENTO']),
            data=strptime_or_default(itens[9]['IT-DA-INICIO-OCOR-AFASTAMENTO'], '%Y%m%d'),
            data_termino=strptime_or_default(itens[9]['IT-DA-TERMINO-OCOR-AFASTAMENTO'], '%Y%m%d'),
        )
        self.assertEqual(so_sem_dipl.diploma_legal, None)

    def _test_importar_servidor2(self):
        """ Testa a função importar_servidor2() com valores simples
            Testamos aqui somente os campos que estão diretamente relacionados 
            ao objeto Servidor, que não precisam criar outro objeto (como ocorrencias). 
            Para testar casos em que devem ser criados/manipulados outros objetos, 
            temos teste mais especializados
        """
        itens = self.criar_servidores_dict()
        self.i.importar_servidor1(itens)
        itens = self.criar_servidores_dict2()
        self.i.importar_servidor2(itens)
        servidor, created = Servidor.objects.get_or_create(matricula='10')
        self.assertFalse(created)

        self.assertEqual(servidor.nascimento_data, strptime_or_default(itens[0]['IT-DA-NASCIMENTO'], '%Y%m%d').date())
        self.assertEqual(servidor.sexo, itens[0]['IT-CO-SEXO'])
        self.assertEqual(servidor.qtde_depend_ir, int(itens[0]['IT-QT-DEPENDENTE-IR']))

        # Dados da carteira de trabalho
        self.assertEqual(servidor.ctps_numero, itens[0]['IT-NU-CARTEIRA-TRABALHO'])
        self.assertEqual(servidor.ctps_serie, itens[0]['IT-NU-SERIE-CARTEIRA-TRABALHO'])
        self.assertEqual(servidor.ctps_uf, itens[0]['IT-SG-UF-CTRA-SERVIDOR'])
        self.assertEqual(servidor.ctps_data_prim_emprego, strptime_or_default(itens[0]['IT-DA-PRIMEIRO-EMPREGO'], '%Y%m%d').date())

        self.assertEqual(servidor.data_cadastro_siape, strptime_or_default(itens[0]['IT-DA-CADASTRAMENTO-SERVIDOR'], '%Y%m%d').date())
        self.assertEqual(servidor.nivel_escolaridade, NivelEscolaridade.objects.get(codigo=itens[0]['IT-CO-NIVEL-ESCOLARIDADE']))
        self.assertEqual(servidor.jornada_trabalho, JornadaTrabalho.objects.get(codigo=itens[0]['IT-CO-JORNADA-TRABALHO']))

        # self.assertEqual(servidor.numerador_prop_aposentadoria, itens[0]['IT-NU-NUMERADOR-PROP'])
        # self.assertEqual(servidor.denominador_prop_aposentadoria, itens[0]['IT-NU-DENOMINADOR-PROP'])
        # self.assertEqual(servidor.num_processo_aposentadoria, str(int(itens[0]['IT-NU-PROCESSO-APOSENTADORIA'])))

        # Dados de ingresso no servico publico
        ingresso_servico_publico = ServidorOcorrencia.objects.filter(
            servidor=servidor,
            ocorrencia=Ocorrencia.objects.get(codigo=itens[0]['IT-CO-GRUPO-OCOR-INGR-SPUB'] + itens[0]['IT-CO-OCOR-INGR-SPUB']),
            subgrupo__descricao='INCLUSAO NO SERVICO PUBLICO',
        ).count()
        self.assertEqual(1, ingresso_servico_publico)
        # Dados de ingresso no orgao
        ingresso_orgao = ServidorOcorrencia.objects.filter(
            servidor=servidor,
            ocorrencia=Ocorrencia.objects.get(codigo=itens[0]['IT-CO-GRUPO-OCOR-INGR-ORGAO'] + itens[0]['IT-CO-OCOR-INGR-ORGAO']),
            subgrupo__descricao='INCLUSAO NO ORGAO',
        ).count()
        self.assertEqual(1, ingresso_orgao)

        # Dados do servidor 2
        servidor2, created = Servidor.objects.get_or_create(matricula='20')
        self.assertFalse(created)
        # self.assertEqual(servidor2.numerador_prop_aposentadoria, None)
        # self.assertEqual(servidor2.denominador_prop_aposentadoria, '00')
        # self.assertEqual(servidor2.num_processo_aposentadoria, '')
        self.assertEqual(servidor2.qtde_depend_ir, 0)
        self.assertEqual(servidor2.ctps_uf, '')
        self.assertEqual(servidor2.funcao.codigo, 'CD')

    def _test_importar_servidor3(self):
        """ Testa a função importar_servidor3() com valores simples
            Testamos aqui somente os campos que estão diretamente relacionados ao objeto Servidor, 
            que não precisam criar outro objeto (como ocorrencias). 
            Para testar casos em que devem ser criados/manipulados outros objetos, temos teste mais especializados
        """
        itens = self.criar_servidores_dict()
        self.i.importar_servidor1(itens)
        itens = self.criar_servidores_dict2()
        self.i.importar_servidor2(itens)
        itens = self.criar_servidores_dict3()
        self.i.importar_servidor3(itens)
        servidor = Servidor.objects.get(matricula='10')
        self.assertEqual(servidor.matricula_anterior, '1041781')

        # Dados do RG
        self.assertEqual(servidor.rg, '332653')
        self.assertEqual(servidor.rg_orgao, 'SSP')
        self.assertEqual(servidor.rg_data, date(1975, 1, 13))
        self.assertEqual(servidor.rg_uf, 'RN')

        self.assertEqual(servidor.data_obito, date(2011, 3, 1))
        self.assertEqual(servidor.titulo_numero, '024783851610')
        self.assertEqual(servidor.opera_raio_x, True)
        self.assertEqual(servidor.codigo_vaga, '0313710')

        self.assertEqual(servidor.setor_exercicio, Setor.todos.get(codigo='000000030'))
        self.assertEqual(servidor.titulacao, Titulacao.objects.get(codigo='23'))

        # Dados do servidor 200
        servidor2 = Servidor.objects.get(matricula='20')

        self.assertEqual(servidor2.matricula_anterior, '2041782')
        self.assertEqual(servidor2.rg, '432654')
        self.assertEqual(servidor2.rg_orgao, 'ITEP')
        self.assertEqual(servidor2.rg_data, date(1985, 1, 10))
        self.assertEqual(servidor2.rg_uf, 'RJ')

        self.assertEqual(servidor2.data_obito, None)
        self.assertEqual(servidor2.titulo_numero, '034783851613')
        self.assertEqual(servidor2.opera_raio_x, False)
        self.assertEqual(servidor2.codigo_vaga, '2313712')

        self.assertEqual(servidor2.setor_exercicio, Setor.todos.get(codigo='000000035'))
        self.assertEqual(servidor2.titulacao, Titulacao.objects.get(codigo='25'))

        # Dados do servidor 3 - campos vazios
        servidor3 = Servidor.objects.get(matricula='30')
        self.assertEqual(servidor3.setor_exercicio, None)
        self.assertEqual(servidor3.titulacao, None)

    def _test_importar_servidor4(self):
        """ Testa a função importar_servidor4() com valores simples
            Testamos aqui somente os campos que estão diretamente relacionados ao objeto Servidor, 
            que não precisam criar outro objeto (como ocorrencias). 
            Para testar casos em que devem ser criados/manipulados outros objetos, temos teste mais especializados
        """
        Configuracao(app='comum', chave='dominios_institucionais', valor='dominio.edu.br').save()

        itens = self.criar_servidores_dict()
        self.i.importar_servidor1(itens)

        itens = self.criar_servidores_dict4()
        self.i.importar_servidor4(itens)

        servidor = Servidor.objects.get(matricula='10')

        #        self.assertEqual(servidor.email_siape, '100@email.secundario')
        self.assertEqual(servidor.grupo_sanguineo, 'AB')
        self.assertEqual(servidor.fator_rh, '+')

        servidor2 = Servidor.objects.get(matricula='20')
        self.assertEqual(servidor2.grupo_sanguineo, 'NI')

    def _test_importar_servidor5(self):
        """ Testa a função importar_servidor5() com valores simples
            Testamos aqui somente os campos que estão diretamente relacionados
            ao objeto Servidor, que não precisam criar outro objeto (como ocorrencias). 
            Para testar casos em que devem ser criados/manipulados outros objetos,
            temos teste mais especializados
        """
        itens = self.criar_servidores_dict()
        self.i.importar_servidor1(itens)
        itens = self.criar_servidores_dict5()
        self.i.importar_servidor5(itens)
        servidor = Servidor.objects.get(matricula='10')

        self.assertEqual(servidor.nome_pai, 'Pai do Servidor 100')
        self.assertEqual(servidor.nascimento_municipio, Municipio.objects.get(nome='MUNICIPIO DE NASCIMENTO', uf='RN'))

        self.assertEqual(servidor.titulo_uf, 'RN')
        self.assertEqual(servidor.titulo_zona, '001')
        self.assertEqual(servidor.titulo_secao, '0123')
        self.assertEqual(servidor.titulo_data_emissao, date(1990, 2, 3))

        self.assertEqual(servidor.cnh_carteira, '0319900203')
        self.assertEqual(servidor.cnh_registro, '0101230123')
        self.assertEqual(servidor.cnh_categoria, '3973402661')
        self.assertEqual(servidor.cnh_uf, 'RN')
        self.assertEqual(servidor.cnh_emissao, date(1999, 3, 4))
        self.assertEqual(servidor.cnh_validade, date(2012, 3, 4))

        #        self.assertEqual(PessoaTelefone.objects.filter(pessoa = servidor.pessoafisica,
        #                                                      numero = '(84) 8986-0460').count(), 1)

        self.assertEqual(servidor.identificacao_unica_siape, '000001001')

        # Verificando se o servidor de matricula 101 também foi atualizado,
        #    já que possui o mesmo CPF que o da matraicula 100
        servidor10 = Servidor.objects.get(matricula='100')

        self.assertEqual(servidor10.nome_pai, 'Pai do Servidor 100')
        self.assertEqual(servidor10.nascimento_municipio, Municipio.objects.get(nome='MUNICIPIO DE NASCIMENTO', uf='RN'))

        self.assertEqual(servidor10.titulo_uf, 'RN')
        self.assertEqual(servidor10.titulo_zona, '001')
        self.assertEqual(servidor10.titulo_secao, '0123')
        self.assertEqual(servidor10.titulo_data_emissao, date(1990, 2, 3))

        self.assertEqual(servidor10.cnh_carteira, '0319900203')
        self.assertEqual(servidor10.cnh_registro, '0101230123')
        self.assertEqual(servidor10.cnh_categoria, '3973402661')
        self.assertEqual(servidor10.cnh_uf, 'RN')
        self.assertEqual(servidor10.cnh_emissao, date(1999, 3, 4))
        self.assertEqual(servidor10.cnh_validade, date(2012, 3, 4))

        list_pessoa_telefone_servidor1 = PessoaTelefone.objects.filter(pessoa__id=servidor.pessoafisica.pessoa_ptr.id)
        list_pessoa_telefone_servidor10 = PessoaTelefone.objects.filter(pessoa__id=servidor10.pessoafisica.pessoa_ptr.id)
        self.assertEqual(list_pessoa_telefone_servidor1.count(), list_pessoa_telefone_servidor10.count())

    #        self.assertTrue(list_pessoa_telefone_servidor1.count()>0)

    def _test_ferias(self):
        """ Testa a função importar_ferias() com valores simples
            Testamos aqui somente os campos que estão diretamente relacionados
            ao objeto Ferias.
        """
        if 'ferias' in settings.INSTALLED_APPS:
            Ferias = apps.get_model('ferias', 'ferias')
            itens = self.criar_servidores_dict()
            self.i.importar_servidor1(itens)
            itens = self.criar_ferias_servidor_dict()
            self.i.importar_historico_ferias(itens)
            servidor1, created = Servidor.objects.get_or_create(matricula='10')
            self.assertFalse(created)
            servidor2, created = Servidor.objects.get_or_create(matricula='20')
            self.assertFalse(created)
            ferias_servidor1 = Ferias.objects.filter(servidor=servidor1)
            ferias_servidor2 = Ferias.objects.filter(servidor=servidor2)
            self.assertTrue(ferias_servidor2.count() == 1)
            self.assertFalse(ferias_servidor1.count() == 2)

    def _test_get_map_layout_functions(self):
        """ Testa se todos os arquivos em ordem estão devidamente mapeados para uma função """
        map_functions = self.i._get_map_layout_functions()
        for arquivo in self.i.ordem:
            map_functions[arquivo]
