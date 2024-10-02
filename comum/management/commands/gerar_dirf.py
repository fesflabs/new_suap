# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from djtools.utils import cpf_valido


class Command(BaseCommandPlus):
    help = 'Gerar os arquivos DIRFs de cada campus de acordo com planilha recebida'

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('planilha', type=str, help='Planilha com os dados')
        parser.add_argument('dirfs', type=str, help='Local onde os arquivos DIRFs vão ser gerados')

    def handle(self, *args, **options):
        planilha = options['planilha']
        dirfs = options['dirfs']
        self.gerar_dirf(planilha, dirfs)

    def gerar_dirf(self, planilha, dirfs):
        RTRT = 'RTRT'
        RTPO = 'RTPO'
        RTIRF = 'RTIRF'
        RIO = 'RIO'

        DIRF = 'DIRF'
        RESPO = 'RESPO'
        DECPJ = 'DECPJ'
        IDREC = 'IDREC'

        def set_linha(linha):
            self.linha = linha

        def get_valor(numero_celula):
            return self.planilha.cell_value(self.linha, numero_celula)

        def add_valor(valor, file):
            if valor == '' or valor == 0.0:
                valor = ''
            else:
                valor = '{:.2f}'.format(valor).replace('.', '')

            file.write('%s|' % valor)

        import xlrd

        workbook = xlrd.open_workbook(planilha)
        self.planilha = workbook.sheet_by_index(0)
        siafi = dict()
        for i in range(1, self.planilha.nrows):
            set_linha(i)
            nome_campus = get_valor(16).strip()
            cnpj_campus = int(get_valor(15))

            siafi[cnpj_campus] = dict()
            siafi[cnpj_campus]['cnpj'] = cnpj_campus
            siafi[cnpj_campus]['nome'] = nome_campus
            siafi[cnpj_campus][IDREC] = dict()

            dirf = dict()
            dirf['ano_referencia'] = int(get_valor(1))
            dirf['ano_calendario'] = int(get_valor(2))
            dirf['identificador_retificadora'] = get_valor(3)
            dirf['numero_recibo'] = get_valor(4)
            dirf['identificador_estrutura_layout'] = get_valor(5)
            siafi[cnpj_campus][DIRF] = dirf

            respo = dict()
            respo['cpf'] = int(get_valor(7))
            respo['nome'] = get_valor(8)
            respo['ddd'] = int(get_valor(9))
            respo['telefone'] = int(get_valor(10))
            respo['ramal'] = int(get_valor(11))
            respo['fax'] = int(get_valor(12))
            respo['correio_eletronico'] = get_valor(13)
            siafi[cnpj_campus][RESPO] = respo

            decpj = dict()
            decpj['cnpj'] = cnpj_campus
            decpj['nome_empresarial'] = nome_campus
            decpj['natureza_declarante'] = int(get_valor(17))
            decpj['cpf_responsavel_cnpj'] = get_valor(18)
            decpj['isorscp'] = get_valor(19)
            decpj['iddcddj'] = get_valor(20)
            decpj['idiaifci'] = get_valor(21)
            decpj['idrprde'] = get_valor(22)
            decpj['ippas'] = get_valor(23)
            decpj['iprjojp'] = get_valor(24)
            decpj['ieudmcssvrrtnoreos'] = get_valor(25)
            decpj['ised'] = get_valor(26)
            decpj['data_evento'] = get_valor(27)
            siafi[cnpj_campus][DECPJ] = decpj

        self.planilha = workbook.sheet_by_index(1)
        inconsistencias = list()
        for i in range(1, self.planilha.nrows):
            set_linha(i)
            cnpj_campus = int(get_valor(1))
            idrec_codigo_receita = get_valor(3)
            idrec = siafi[cnpj_campus][IDREC]
            if idrec_codigo_receita not in idrec:
                idrec[idrec_codigo_receita] = dict()
                idrec[idrec_codigo_receita]['declarantes'] = dict()

            declarantes = idrec[idrec_codigo_receita]['declarantes']
            cpf = get_valor(5)
            if isinstance(cpf, str):
                cpf = cpf.replace('-', '').replace('.', '')
            cpf = '{:011d}'.format(int(cpf))
            nome = get_valor(6).replace('.', ' ')

            declarante = dict()
            declarante['nome'] = nome
            declarante['cpf'] = cpf
            self.cpf = cpf

            rtrt = get_valor(10)
            if rtrt == RTRT:
                rtrt = dict()
                rtrt['valores'] = [get_valor(i) for i in range(11, 24)]
                declarante[RTRT] = rtrt

            rtpo = get_valor(24)
            if rtpo == RTPO:
                rtpo = dict()
                rtpo['valores'] = [get_valor(i) for i in range(25, 38)]
                declarante[RTPO] = rtpo

            rtirf = get_valor(38)
            if rtirf == RTIRF:
                rtirf = dict()
                rtirf['valores'] = [get_valor(i) for i in range(39, 52)]
                declarante[RTIRF] = rtirf

            rio = get_valor(52)
            if rio == RIO:
                rio = dict()
                rio['valor'] = get_valor(53)
                rio['descricao'] = get_valor(54)
                declarante[RIO] = rio

            declarantes[cpf] = declarante
            if not cpf_valido(cpf):
                inconsistencias.append("{} {}".format(cpf, nome))

        import subprocess

        # Não tem o cadastro dos CNPJs no SUAP
        for cnpj_campus, siafi_campus in list(siafi.items()):
            ug = cnpj_campus
            if ug == 10877412000591:
                ug = 'AP'
            elif ug == 10877412001210:
                ug = 'CA'
            elif ug == 10877412001300:
                ug = 'CAL'
            elif ug == 10877412001806:
                ug = 'CANG'
            elif ug == 10877412001997:
                ug = 'CM'
            elif ug == 10877412001130:
                ug = 'CN'
            elif ug == 10877412001059:
                ug = 'CNAT'
            elif ug == 10877412000320:
                ug = 'IP'
            elif ug == 10877412000834:
                ug = 'JC'
            # elif ug == u'':
            #     ug = u'JUC'
            # elif ug == u'':
            #     ug = u'LAJ'
            elif ug == 10877412000753:
                ug = 'MC'
            elif ug == 10877412000400:
                ug = 'MO'
            elif ug == 10877412001563:
                ug = 'NC'
            # elif ug == u'':
            #     ug = u'PAAS'
            elif ug == 10877412001482:
                ug = 'PAR'
            elif ug == 10877412000672:
                ug = 'PF'
            elif ug == 10877412000249:
                ug = 'SC'
            elif ug == 10877412001644:
                ug = 'SGA'
            elif ug == 10877412001725:
                ug = 'SPO'
            # elif ug == 10877412001059: # igual ao do CNAT
            #     ug = u'ZL'
            elif ug == 10877412000915:
                ug = 'ZN'
            elif ug == 10877412000168:
                ug = 'RE'

            caminho_arquivo = '{}/dirf_{}.txt'.format(dirfs, ug)
            f = open('/tmp/dirf_temp', 'w')

            dirf = siafi_campus[DIRF]
            f.write(
                'DIRF|{}|{}|{}|{}|{}|\n'.format(
                    dirf['ano_referencia'], dirf['ano_calendario'], dirf['identificador_retificadora'], dirf['numero_recibo'], dirf['identificador_estrutura_layout']
                )
            )

            respo = siafi_campus[RESPO]
            f.write('RESPO|{}|{}|{}|{}|{}|{}||\n'.format(respo['cpf'], respo['nome'], respo['ddd'], respo['telefone'], respo['ramal'], respo['fax']))

            decpj = siafi_campus[DECPJ]
            f.write(
                'DECPJ|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|\n'.format(
                    decpj['cnpj'],
                    decpj['nome_empresarial'],
                    decpj['natureza_declarante'],
                    decpj['cpf_responsavel_cnpj'],
                    decpj['isorscp'],
                    decpj['iddcddj'],
                    decpj['idiaifci'],
                    decpj['idrprde'],
                    decpj['ippas'],
                    decpj['iprjojp'],
                    decpj['ieudmcssvrrtnoreos'],
                    decpj['ised'],
                    decpj['data_evento'],
                )
            )
            for codigo_receita in sorted(siafi_campus[IDREC].keys()):
                dados = siafi_campus[IDREC][codigo_receita]
                f.write('IDREC|{:04}|\n'.format(int(codigo_receita)))
                declarantes = dados['declarantes']
                cpfs = list(declarantes.keys())
                for cpf in sorted(cpfs):
                    declarante = declarantes[cpf]
                    f.write('BPFDEC|{:011d}|{}||N|N|\n'.format(int(cpf.replace('-', '')), declarante['nome'][:60]))
                    if RTRT in declarante:
                        f.write('RTRT|')
                        for valor in declarante[RTRT]['valores']:
                            add_valor(valor, f)
                        f.write('\n')

                    if RTPO in declarante:
                        f.write('RTPO|')
                        for valor in declarante[RTPO]['valores']:
                            add_valor(valor, f)
                        f.write('\n')

                    if RTIRF in declarante:
                        f.write('RTIRF|')
                        for valor in declarante[RTIRF]['valores']:
                            add_valor(valor, f)
                        f.write('\n')

                    if RIO in declarante:
                        f.write('RIO|')
                        add_valor(declarante[RIO]['valor'], f)
                        f.write('{}|'.format(declarante[RIO]['descricao']))
                        f.write('\n')

            f.write('FIMDIRF|')
            f.close()
            temp = open(caminho_arquivo, 'w')
            args = ['iconv', '--from-code=UTF-8', '--to-code=ISO-8859-1', f.name]
            subprocess.call(args, stdout=temp)
            temp.close()
