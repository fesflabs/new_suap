# -*- coding: utf-8 -*-
import sys

from django.utils import termcolors

from financeiro.importador import get_itens
from rh.models import UnidadeOrganizacional, Servidor

DIRETORIO_BASE = '/home/adelson/Adelson ANTIGO/Área de Trabalho/SUAP-DOC/ADM/IRR/AUDITORIA-CGU/'


def processar_ob():

    CPF = 'IT-CO-FAVORECIDO'
    UG = 'IT-CO-UG-DOC-REFERENCIA'
    VALOR = 'IT-VA-EVENTO-SISTEMA'
    DATA = 'IT-DA-EMISSAO'
    # NE = 'IT-DA-EMISSAO'
    LISTA = 'IT-SQ-LISTA'

    def is_ne_pronatec(data, nes):
        ug = data.get(UG)
        for i in range(1, 101):
            if 'IT-CO-INSCRICAO1(%s)' % i in data and ug + '26435' + data.get('IT-CO-INSCRICAO1(%s)' % i) in nes:
                return True
            if 'IT-CO-INSCRICAO2(%s)' % i in data and ug + '26435' + data.get('IT-CO-INSCRICAO2(%s)' % i) in nes:
                return True
            if 'IT-CO-INSCRICAO01(%s)' % i in data and ug + '26435' + data.get('IT-CO-INSCRICAO01(%s)' % i) in nes:
                return True
            if 'IT-CO-INSCRICAO02(%s)' % i in data and ug + '26435' + data.get('IT-CO-INSCRICAO02(%s)' % i) in nes:
                return True
        return False

    nes = set()
    # arquivo_siafi = csv.reader(open(DIRETORIO_BASE+"NE's Pronatec 2014.csv"), delimiter=',')
    # for idx, row in enumerate(arquivo_siafi):
    #     if idx != 0:
    #         nes.add(row[1]+row[5])
    # arquivo_siafi = csv.reader(open(DIRETORIO_BASE+"NE's pronatec de 2014 pagos em 2015.csv"), delimiter=',')
    # for idx, row in enumerate(arquivo_siafi):
    #     if idx != 0:
    #         nes.add(row[1]+row[2])
    print('\nLendo NEs de 2014')
    temp_nes = get_itens(DIRETORIO_BASE + '2014/nota_ne_20150612.REF', DIRETORIO_BASE + '2014/nota_ne_20150612.TXT')
    total = len(temp_nes)
    count = 0
    for ne in temp_nes:
        count += 1
        porcentagem = int(float(count) / total * 100)
        sys.stdout.write(termcolors.make_style(fg='cyan', opts=('bold',))('\r[{0}] {1}% - Processando NE {2} de {3}'.format('#' * (porcentagem / 10), porcentagem, count, total)))
        sys.stdout.flush()
        ne = dict((k, v) for k, v in list(ne.items()) if v)
        # Recursos de 2014
        # Naturezas de Despesa: 339036 e 339048
        if 'GR-NATUREZA-DESPESA' in ne and ne['GR-NATUREZA-DESPESA'] in ('339036', '339048'):
            # PI: QFP05P0601P
            if ne['IT-CO-PLANO-INTERNO'] == 'QFP05P0601P':
                # # PTRES: 061645
                # if ne['IT-CO-PROGRAMA-TRABALHO-RESUMIDO'] == '061645':
                #     # Fonte: 0112915153
                #     if ne['GR-FONTE-RECURSO'] == '0112915153':
                #         # UG do campus + UG do IFRN + número da NE
                #         nes.add(ne['GR-UG-GESTAO-AN-NUMERO-NEUQ(1)'])
                nes.add(ne['GR-UG-GESTAO-AN-NUMERO-NEUQ(1)'])

    print('\nLendo NEs de 2015')
    temp_nes_2015 = get_itens(DIRETORIO_BASE + 'nota_ne_20151207.REF', DIRETORIO_BASE + 'nota_ne_20151207.TXT')
    total = len(temp_nes_2015)
    count = 0
    for ne in temp_nes_2015:
        count += 1
        porcentagem = int(float(count) / total * 100)
        sys.stdout.write(termcolors.make_style(fg='cyan', opts=('bold',))('\r[{0}] {1}% - Processando NE {2} de {3}'.format('#' * (porcentagem / 10), porcentagem, count, total)))
        sys.stdout.flush()
        ne = dict((k, v) for k, v in list(ne.items()) if v)
        # Recursos de 2015
        # Naturezas de Despesa: 339036 e 339048
        if 'GR-NATUREZA-DESPESA' in ne and ne['GR-NATUREZA-DESPESA'] in ('339036', '339048'):
            # PI: LFP05P1901N
            if ne['IT-CO-PLANO-INTERNO'] == 'LFP05P1901N':
                # # PTRES: 087416
                # if ne['IT-CO-PROGRAMA-TRABALHO-RESUMIDO'] == '087416':
                #     # Fonte: 0112915153
                #     if ne['GR-FONTE-RECURSO'] == '0112915153':
                #         # UG do campus + UG do IFRN + número da NE
                #         nes.add(ne['GR-UG-GESTAO-AN-NUMERO-NEUQ(1)'])
                nes.add(ne['GR-UG-GESTAO-AN-NUMERO-NEUQ(1)'])

    print('\nLendo LCs')
    temp_lcs = get_itens(DIRETORIO_BASE + 'lc2015_lc_20151204.REF', DIRETORIO_BASE + 'lc2015_lc_20151204.TXT')
    lcs = dict()
    total = len(temp_lcs)
    count = 0
    for lc in temp_lcs:
        count += 1
        porcentagem = int(float(count) / total * 100)
        sys.stdout.write(termcolors.make_style(fg='cyan', opts=('bold',))('\r[{0}] {1}% - Processando LC {2} de {3}'.format('#' * (porcentagem / 10), porcentagem, count, total)))
        sys.stdout.flush()
        lc = dict((k, v) for k, v in list(lc.items()) if v)
        if 'GR-AN-NU-OB-CANCELAMENTO' not in lc:
            # data = lc['IT-DA-TRANSACAO']
            numero = lc['GR-UG-GESTAO-AN-NUMERO-LC']
            cpf = lc[CPF]
            valor = lc['IT-VA-CREDOR']

            if numero not in lcs:
                lcs[numero] = dict()
            favorecidos = lcs[numero]

            if cpf not in favorecidos:
                favorecidos[cpf] = valor

    print('\nLendo OBs')
    temp_obs = get_itens(DIRETORIO_BASE + 'ob_ob_20151204.REF', DIRETORIO_BASE + 'ob_ob_20151204.TXT')
    obs = list()
    for ob in temp_obs:
        ob = dict((k, v) for k, v in list(ob.items()) if v)
        obs.append(ob)

    obss = list()
    for item in obs:
        if '158370264352015OB800206' in item['GR-UG-GESTAO-AN-NUMERO-OBUQ']:
            obss.append(item)

    obs_cancelados = list()
    obs_pagos = list()
    total = len(obs)
    count = 0
    for item in obs:
        count += 1
        porcentagem = int(float(count) / total * 100)
        sys.stdout.write(termcolors.make_style(fg='cyan', opts=('bold',))('\r[{0}] {1}% - Processando OB {2} de {3}'.format('#' * (porcentagem / 10), porcentagem, count, total)))
        sys.stdout.flush()

        item = dict((k, v) for k, v in list(item.items()) if v)

        # if '158370264352015OB800206' in item['GR-UG-GESTAO-AN-NUMERO-OBUQ']:
        #     import ipdb; ipdb.set_trace()

        if item['IT-IN-TIPO-OB'] in ('11', '12', '13'):
            # item['IT-IN-FAVORECIDO'] == '1' Pessoa Jurídica
            # item['IT-IN-FAVORECIDO'] == '2' Pessoa Fisica
            if item['IT-IN-FAVORECIDO'] in ['1', '2']:
                # if is_nd_pronatec(get_gr_classificacao(item)):
                if is_ne_pronatec(item, nes):
                    if 'GR-AN-NU-OB-CANCELAMENTO' in item:  # CANCELADOS
                        obs_cancelados.append(item)
                    # elif item.has_key('IT-IN-CANCELAMENTO-OB'): #PARCIALMENTE CANCELADOS
                    #     obs_outros_cancelados_parcialmente.append(item)
                    else:
                        obs_pagos.append(item)

    obs_ugs = dict()
    for ob in obs_pagos:
        cpf = ob[CPF]
        ug = ob[UG]
        valor = ob[VALOR]
        mes = ob[DATA].month
        if ug not in obs_ugs:
            obs_ugs[ug] = dict()

        favorecidos_ug = obs_ugs[ug]

        if ob['IT-IN-FAVORECIDO'] == '1':
            if LISTA in ob:
                lista = ob[LISTA]
                # ug uo ano LC numero
                numero_lista = '%s264352015LC%s' % (ug, lista)
                if numero_lista in lcs:
                    favorecidos = lcs[numero_lista]
                    for cpf_favorecido in favorecidos:

                        if cpf_favorecido not in favorecidos_ug:
                            favorecidos_ug[cpf_favorecido] = dict()
                        favorecido = favorecidos_ug[cpf_favorecido]
                        try:
                            valor = lcs[numero_lista][cpf_favorecido]
                        except Exception:
                            print()
                        if mes not in favorecido:
                            favorecido[mes] = dict()
                            favorecido[mes]['valor'] = list()
                        favorecido[mes]['valor'].append(valor)
            # else:
            #     import ipdb; ipdb.set_trace()
            #     pass
        else:
            if cpf not in favorecidos_ug:
                favorecidos_ug[cpf] = dict()
            favorecido = favorecidos_ug[cpf]

            if mes not in favorecido:
                favorecido[mes] = dict()
                favorecido[mes]['valor'] = list()
                favorecido[mes]['classificacao'] = list()
            favorecido[mes]['valor'].append(valor)

    gerar_csv_obs(obs_ugs)


def gerar_csv_obs(obs):
    import io

    f = io.open(DIRETORIO_BASE + 'pronatec.csv', 'w', encoding='utf8')
    for ug, siafi_campus in list(obs.items()):
        if ug == '158371':
            ug = 'AP'
        elif ug == '158370':
            ug = 'CA'
        elif ug == '152711':
            ug = 'CAL'
        elif ug == '154839':
            ug = 'CANG'
        elif ug == '154838':
            ug = 'CM'
        elif ug == '158366':
            ug = 'CN'
        elif ug == '158369':
            ug = 'CNAT'
        # elif ug == u'158369':
        #     ug = u'EAD'
        elif ug == '158367':
            ug = 'IP'
        elif ug == '158373':
            ug = 'JC'
        # elif ug == u'':
        #     ug = u'LAJ'
        elif ug == '158375':
            ug = 'MC'
        elif ug == '158365':
            ug = 'MO'
        elif ug == '152757':
            ug = 'NC'
        # elif ug == u'':
        #     ug = u'PAAS'
        elif ug == '152756':
            ug = 'PAR'
        elif ug == '158374':
            ug = 'PF'
        elif ug == '158372':
            ug = 'SC'
        elif ug == '154582':
            ug = 'SGA'
        elif ug == '154840':
            ug = 'SPP'
        elif ug == '158368':
            ug = 'ZN'
        elif ug == '158155':
            ug = 'RE'

        sigla = ug
        campus = UnidadeOrganizacional.objects.suap().get(sigla=sigla)
        cpfs = list(siafi_campus.keys())
        cpfs.sort()
        for cpf in cpfs:
            servidor = Servidor.get_by_cpf_ou_matricula(cpf)
            if servidor:
                nome = servidor.pessoa_fisica.nome
                situacao = servidor.situacao or ''
                cargo_emprego = servidor.cargo_emprego or ''
                jornada_trabalho = servidor.jornada_trabalho or ''
                funcao = servidor.funcao or ''
            else:
                continue
            declarante = siafi_campus[cpf]
            for mes in range(1, 13):
                try:
                    # data = '1/%d/2015' % mes
                    valores = {'valor': ['0'], 'classificacao': ['0']}
                    if mes in list(declarante.keys()):
                        valores = declarante[mes]

                    f.write('%s, ' % campus.nome)
                    f.write('%s, ' % cpf)
                    f.write('%s, ' % nome.strip())
                    f.write('%s, ' % situacao)
                    f.write('%s, ' % cargo_emprego)
                    f.write('%s, ' % jornada_trabalho)
                    f.write('%s ' % funcao)
                    linha = ''
                    for idx, valor in enumerate(valores['valor']):
                        linha += ', %s' % valor
                    f.write(linha)
                    f.write('\n')
                except Exception:
                    print('')
                    pass

    f.close()
