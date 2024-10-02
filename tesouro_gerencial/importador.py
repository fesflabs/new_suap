# -*- coding: utf-8 -*-
import csv
import decimal
import re
import sys
from django.conf import settings
from datetime import datetime

from tesouro_gerencial.models import (
    NotaCredito,
    RAP,
    ReceitaGRU,
    UnidadeGestora,
    GRU,
    RAPItem,
    ClassificacaoInstitucional,
    AcaoGoverno,
    ProgramaTrabalhoResumido,
    PlanoInterno,
    FonteRecurso,
    NaturezaDespesa,
    SubElementoNaturezaDespesa,
    EsferaOrcamentaria,
    NotaCreditoItem,
    ContaContabil,
    DocumentoEmpenho,
    DocumentoLiquidacao,
    DocumentoPagamento,
    DocumentoBase,
    DocumentoEmpenhoItem,
    DocumentoPagamentoItem,
    DocumentoLiquidacaoItem,
)

'''
* Verificar a possibilidade de trabalhar melhor a criação dos PTRES
'''


class MyCache(object):
    def __init__(self):
        self._cache = dict()

    def get_item(self, key, item):
        if key in self._cache and item in self._cache[key]:
            return self._cache[key][item]
        return None

    def add_item(self, key, item, obj):
        if key not in self._cache:
            self._cache[key] = dict()
        self._cache[key][item] = obj


class Importador(object):
    LOG_PRINT = 1
    LOG_ARQUIVO = 0

    _cache = MyCache()

    def __init__(self, arquivos, encoding='ISO-8859-1', tipo_log=LOG_PRINT, log_level=1, log_nome_arquivo=f'{settings.BASE_DIR}/deploy/logs/siafi_log.txt'):
        self.ini_row = 0
        self.ignore_last_row = False
        self.arquivos = arquivos
        self.encoding = encoding
        self.tipo_log = tipo_log
        self.log_level = log_level
        self.log_nome_arquivo = log_nome_arquivo
        self.ordenar = False

    def log(self, txt, tipo_log=-1):
        if tipo_log == -1:
            tipo_log = self.tipo_log
        self.stdout = open(self.log_nome_arquivo, 'a') if tipo_log == self.LOG_ARQUIVO else sys.stdout
        self.stdout.write(txt)

    def format_data(self, data):
        dia, mes, ano = data.split('/')
        return datetime(year=int(ano), month=int(mes), day=int(dia))

    def get_conta_contabil(self, codigo, nome):
        self.log(u'Obtendo Conta Contábil - %s...\n' % codigo)
        conta_contabil = self._cache.get_item('conta_contabil', codigo)
        if conta_contabil is None:
            conta_contabil, _ = ContaContabil.objects.get_or_create(codigo=codigo, defaults={'nome': nome})
            self._cache.add_item('conta_contabil', codigo, conta_contabil)

        return conta_contabil

    def get_unidade_gestora(self, codigo, nome):
        self.log(u'Obtendo Unidade Gestora - %s...\n' % codigo)
        ug = self._cache.get_item('unidade_gestora', codigo)
        if ug is None:
            ug, _ = UnidadeGestora.objects.get_or_create(codigo=codigo, defaults={'nome': nome})
            self._cache.add_item('unidade_gestora', codigo, ug)

        return ug

    def get_classificacao_institucional(self, codigo, nome):
        self.log(u'Obtendo Classificação Institucional - %s...\n' % codigo)
        ci = self._cache.get_item('classificacao_institucional', codigo)

        if ci is None:
            ci, _ = ClassificacaoInstitucional.objects.get_or_create(codigo=codigo, defaults={'nome': nome})
            self._cache.add_item('classificacao_institucional', codigo, ci)

        return ci

    def get_esfera_orcamentaria(self, codigo, nome):
        self.log(u'Obtendo Esfera Orçamentária - %s...\n' % codigo)
        esfera_orcamentaria = self._cache.get_item('esfera_orcamentaria', codigo)
        if esfera_orcamentaria is None:
            esfera_orcamentaria, _ = EsferaOrcamentaria.objects.get_or_create(codigo=codigo, defaults={'nome': nome})
            self._cache.add_item('esfera_orcamentaria', codigo, esfera_orcamentaria)

        return esfera_orcamentaria

    def get_ptres(self, codigo):
        self.log(u'Obtendo PTRES - %s...\n' % codigo)
        ptres = self._cache.get_item('ptres', codigo)
        if ptres is None:
            ptres, _ = ProgramaTrabalhoResumido.objects.get_or_create(codigo=codigo)
            self._cache.add_item('ptres', codigo, ptres)

        return ptres

    def get_fonte_recurso(self, codigo, nome):
        self.log(u'Obtendo Fonte de Recurso - %s...\n' % codigo)
        fonte = self._cache.get_item('fonte_recurso', codigo)
        if fonte is None:
            fonte, _ = FonteRecurso.objects.get_or_create(codigo=codigo, defaults={'nome': nome})
            self._cache.add_item('fonte_recurso', codigo, fonte)

        return fonte

    def get_natureza_despesa(self, codigo, nome):
        self.log(u'Obtendo Naturesa de Despesa - %s...\n' % codigo)
        natureza_despesa = self._cache.get_item('natureza_despesa', codigo)
        if natureza_despesa is None:
            # TODO: ver como fazer, não tem informação sobre  categoria, grupo, modalidade e elemento de despesa
            natureza_despesa, _ = NaturezaDespesa.objects.get_or_create(codigo=codigo, defaults={'nome': nome})
            self._cache.add_item('natureza_despesa', codigo, natureza_despesa)

        return natureza_despesa

    def get_subitem_natureza_despesa(self, natureza_despesa, codigo, nome):
        self.log(u'Obtendo Subitem - {}...\n'.format(codigo))
        sub_codigo = '{}{}'.format(natureza_despesa.codigo, codigo)
        subelemento = self._cache.get_item('subelemento', sub_codigo)
        if subelemento is None:
            subelemento, _ = SubElementoNaturezaDespesa.objects.get_or_create(codigo_subelemento=codigo, natureza_despesa=natureza_despesa, defaults={'nome': nome})
            subelemento.save()
            self._cache.add_item('subelemento', sub_codigo, subelemento)

        return subelemento

    def get_plano_interno(self, codigo, nome):
        self.log(u'Obtendo Plano Interno - {}...\n'.format(codigo))
        plano = self._cache.get_item('plano_interno', codigo)
        if plano is None:
            plano, _ = PlanoInterno.objects.get_or_create(codigo=codigo, defaults={'nome': nome})
            self._cache.add_item('plano_interno', codigo, plano)

        return plano

    def get_acao_governo(self, codigo, nome):
        self.log(u'Obtendo Plano Interno - {}...\n'.format(codigo))
        acao_governo = self._cache.get_item('acao_governo', codigo)
        # TODO: ainda está faltando mais dados para isso ou criar um novo modelo
        if acao_governo is None:
            acao_governo, _ = AcaoGoverno.objects.get_or_create(codigo=codigo, defaults={'nome': nome})
            self._cache.add_item('acao_governo', codigo, acao_governo)

        return acao_governo

    def get_gru(self, codigo, nome):
        self.log(f'Obtendo GRU - {codigo}...\n')
        gru = self._cache.get_item('unidade_gestora', codigo)
        if gru is None:
            gru, _ = GRU.objects.get_or_create(codigo=codigo, defaults={'nome': nome})
            self._cache.add_item('unidade_gestora', codigo, gru)

        return gru

    def get_valor(self, valor):
        if valor:
            return decimal.Decimal(valor.replace('.', '').replace(',', '.').replace('(', '-').replace(')', ''))

        # TODO: ver porque existe essas inconsistências
        return decimal.Decimal(0)

    def iterar(self, rows):
        for row in rows:
            self.processar(row)

    def run(self):
        self.stdout = open(self.log_nome_arquivo, 'a') if self.tipo_log == self.LOG_ARQUIVO else sys.stdout
        conteudo_arquivos = []
        for arquivo in self.arquivos:
            try:
                with open(arquivo, encoding=self.encoding) as file:
                    rows = list(csv.reader(file, delimiter=self.delimiter))
                    nrows = len(rows)
                    if self.ignore_last_row:
                        nrows -= 1

                    rows = rows[self.ini_row: nrows]
                    if rows:
                        ordenar_por = rows[0][0]
                        if hasattr(self, 'ordenar_por'):
                            ordenar_por = rows[0][self.ordenar_por]
                        conteudo_arquivos.append([ordenar_por, rows])
            except Exception:
                self.stdout.write('-' * 79)
                self.stdout.write('\n')
                self.stdout.write(f'Erro ao tentar ler o arquivo {arquivo}')
                self.stdout.write('-' * 79)
                self.stdout.write('\n')

        if self.ordenar:
            conteudo_arquivos = sorted(conteudo_arquivos)

        rows = []
        for conteudo in conteudo_arquivos:
            rows.extend(conteudo[1])

        nrows = len(rows)

        if not self.arquivos:
            sys.stdout.write('-' * 79)
            sys.stdout.write('Numero de linhas     : {}\n'.format(nrows))
            sys.stdout.write('\n')
            sys.stdout.write('Nenhum arquivo encontrado.')
            return

        if isinstance(self.arquivos[0], str):
            nomes_arquivos = ', '.join(self.arquivos)
        else:
            nomes_arquivos = ', '.join([arquivo.path for arquivo in self.arquivos])

        self.stdout.write('-' * 79)
        self.stdout.write('\n')
        self.stdout.write('Iniciando o processando do(s) arquivo(s): {}\n'.format(nomes_arquivos))
        self.stdout.write('-' * 79)
        self.stdout.write('\n')
        self.stdout.write('Numero de linhas     : {}\n'.format(nrows))

        self.iterar(rows)

        if self.stdout is not sys.stdout:
            self.stdout.close()

        sys.stdout.write('Numero de linhas     : {}\n'.format(nrows))
        sys.stdout.write('\n')
        sys.stdout.write('Finalizado o processando do(s) arquivo(s): {}\n'.format(nomes_arquivos))

    def processar(self, row):
        raise NotImplementedError


class ImportadorNotaCredito(Importador):
    NC = 0
    CONTA_CONTABIL = 1
    CONTA_CONTABIL_NOME = 2
    DT_LANC = 3
    DOC_OBS = 4
    UNIDADE_ORCAMENTARIA = 5
    UNIDADE_ORCAMENTARIA_NOME = 6
    EMITENTE_GESTAO = 7
    EMITENTE_GESTAO_NOME = 8
    EMITENTE_UG = 9
    EMITENTE_UG_NOME = 10
    FAVORECIDO_DOC = 11
    FAVORECIDO_DOC_NOME = 12
    ESFERA_ORCAMENTARIA = 13
    ESFERA_ORCAMENTARIA_NOME = 14
    ACAO_GOVERNO = 15
    ACAO_GOVERNO_NOME = 16
    RESPONSAVEL_UG = 17
    RESPONSAVEL_UG_NOME = 18
    PTRES = 19
    PI = 20
    PI_NOME = 21
    FONTE_RECURSO = 22
    FONTE_RECURSO_NOME = 23
    GRUPO_DESPESA = 24
    GRUPO_DESPESA_NOME = 25
    NATUREZA_DESPESA = 26
    NATUREZA_DESPESA_NOME = 27
    SUBITEM = 28
    SUBITEM_NOME = 29
    SALDO_ATUAL = 30

    def __init__(self, *args, **kwargs):
        super(ImportadorNotaCredito, self).__init__(*args, **kwargs)
        self.ini_row = 3
        self.ignore_last_row = True
        self.delimiter = '\t'

        self.stdout = open(self.log_nome_arquivo, 'a') if self.tipo_log == self.LOG_ARQUIVO else sys.stdout
        self.stdout.write('\n\n')
        self.stdout.write('ImportadorNotaCredito')

    def get_nota_credito(self, numero, row):
        self.log(u'Obtendo Nota de Crédito - {}...\n'.format(numero))
        nota_credito = self._cache.get_item('nota_credito', numero)
        if nota_credito is None:
            nota_credito, created = NotaCredito.objects.update_or_create(
                numero=numero,
                defaults=dict(
                    conta_contabil=self.get_conta_contabil(row[self.CONTA_CONTABIL], row[self.CONTA_CONTABIL_NOME]),
                    data_emissao=self.format_data(row[self.DT_LANC]),
                    observacao=row[self.DOC_OBS],
                    unidade_orcamentaria=self.get_classificacao_institucional(row[self.EMITENTE_GESTAO], row[self.EMITENTE_GESTAO_NOME]),
                    emitente_ci=self.get_classificacao_institucional(row[self.EMITENTE_GESTAO], row[self.EMITENTE_GESTAO_NOME]),
                    emitente_ug=self.get_unidade_gestora(row[self.EMITENTE_UG], row[self.EMITENTE_UG_NOME]),
                    favorecido_ug=self.get_unidade_gestora(row[self.FAVORECIDO_DOC], row[self.FAVORECIDO_DOC_NOME]),
                ),
            )
            if created:
                self.log(u'Criando Nota de Crédito: {}\n'.format(numero))
            else:
                self.log(u'Atualizando Nota de Crédito: {}\n'.format(numero))

            self._cache.add_item('nota_credito', numero, nota_credito)

        return nota_credito

    def processar(self, row):
        numero = row[self.NC]
        nota_credito = self.get_nota_credito(numero, row)
        natureza_despesa = self.get_natureza_despesa(row[self.NATUREZA_DESPESA], row[self.NATUREZA_DESPESA_NOME])
        rap_item, created = NotaCreditoItem.objects.update_or_create(
            nota_credito=nota_credito,
            esfera_orcamentaria=self.get_esfera_orcamentaria(row[self.ESFERA_ORCAMENTARIA], row[self.ESFERA_ORCAMENTARIA_NOME]),
            acao_governo=self.get_acao_governo(row[self.ACAO_GOVERNO], row[self.ACAO_GOVERNO_NOME]),
            responsavel_ug=self.get_unidade_gestora(row[self.RESPONSAVEL_UG], row[self.RESPONSAVEL_UG_NOME]),
            ptres=self.get_ptres(codigo=row[self.PTRES]),
            plano_interno=self.get_plano_interno(row[self.PI], row[self.PI_NOME]),
            fonte_recurso=self.get_fonte_recurso(row[self.FONTE_RECURSO], row[self.FONTE_RECURSO_NOME]),
            subitem=self.get_subitem_natureza_despesa(natureza_despesa, row[self.SUBITEM], row[self.SUBITEM_NOME]),
            defaults=dict(
                valor=self.get_valor(row[self.SALDO_ATUAL]),
                naturesa_despesa_original=row[self.NATUREZA_DESPESA],
                grupo_despesa_original=row[self.GRUPO_DESPESA],
            ),
        )
        if created:
            self.log(u'Criando item da Nota de Crédito: {}\n'.format(nota_credito.numero))
        else:
            self.log(u'Atualizando item da Nota de Crédito: {}\n'.format(nota_credito.numero))


class ImportadorExecNE(Importador):
    NE = 0
    DOCUMENTO = 1  # NE, NS, OB, DF, DR, GP, GR
    DT_EMICAO = 2
    UNIDADE_ORCAMENTARIA = 3
    UNIDADE_ORCAMENTARIA_NOME = 4
    ANO_EMICAO = 5
    DOC_OBS = 6
    FAVORECIDO = 7
    FAVORECIDO_NOME = 8
    ACAO_GOVERNO = 9
    ACAO_GOVERNO_NOME = 10
    PTRES = 11
    PI = 12
    PI_NOME = 13
    FONTE_RECURSO = 14
    FONTE_RECURSO_NOME = 15
    ESFERA_ORCAMENTARIA = 16
    ESFERA_ORCAMENTARIA_NOME = 17
    NATUREZA_DESPESA = 18
    NATUREZA_DESPESA_NOME = 19
    SUBITEM = 20
    SUBITEM_NOME = 21
    GRUPO_DESPESA = 22
    GRUPO_DESPESA_NOME = 23
    EXECUTORA_UG = 24
    EXECUTORA_UG_NOME = 25
    RESPONSAVEL_UG = 26
    RESPONSAVEL_UG_NOME = 27
    DESPESAS_EMPENHADAS = 28  # NE
    DESPESAS_LIQUIDADAS = 29  # NS
    DESPESAS_PAGAS = 30  # Diferente de NE e NS

    def __init__(self, *args, **kwargs):
        super(ImportadorExecNE, self).__init__(*args, **kwargs)
        self.ini_row = 5
        self.ordenar = True
        self.ordenar_por = self.DT_EMICAO
        self.delimiter = ','

        self.stdout = open(self.log_nome_arquivo, 'a') if self.tipo_log == self.LOG_ARQUIVO else sys.stdout
        self.stdout.write('\n\n')
        self.stdout.write('ImportadorExecNE')

    def get_tipo(self, numero_documento):
        return re.findall(r'\D+', numero_documento)[0]

    def get_documento_classe(self, tipo):
        ClasseDocumento = None
        if tipo in [DocumentoBase.TIPO_NE, DocumentoBase.TIPO_RO]:
            ClasseDocumento = DocumentoEmpenho
        elif tipo == DocumentoBase.TIPO_NS:
            ClasseDocumento = DocumentoLiquidacao
        elif tipo in [DocumentoBase.TIPO_OB, DocumentoBase.TIPO_DF, DocumentoBase.TIPO_DR, DocumentoBase.TIPO_GP, DocumentoBase.TIPO_GR]:
            ClasseDocumento = DocumentoPagamento

        return ClasseDocumento

    def processar_documento(self, row):
        numero_ne = row[self.NE]
        numero_documento = row[self.DOCUMENTO]
        self.log(u'Adicionando Documento {} da Nota de Empenho: {}\n'.format(numero_documento, numero_ne))
        documento = self._cache.get_item('documento', numero_documento)
        tipo = self.get_tipo(numero_documento)
        if documento is None:
            ClasseDocumento = self.get_documento_classe(tipo)
            documento, created = ClasseDocumento.objects.update_or_create(
                numero=numero_documento,
                defaults=dict(
                    tipo=tipo,
                    data_emissao=self.format_data(row[self.DT_EMICAO]),
                    unidade_orcamentaria=self.get_classificacao_institucional(row[self.UNIDADE_ORCAMENTARIA], row[self.UNIDADE_ORCAMENTARIA_NOME]),
                    observacao=row[self.DOC_OBS],
                    favorecido_codigo=row[self.FAVORECIDO],
                    favorecido_nome=row[self.FAVORECIDO_NOME],
                    acao_governo=self.get_acao_governo(row[self.ACAO_GOVERNO], row[self.ACAO_GOVERNO_NOME]),
                    ptres=self.get_ptres(codigo=row[self.PTRES]),
                    plano_interno=self.get_plano_interno(row[self.PI], row[self.PI_NOME]),
                    fonte_recurso=self.get_fonte_recurso(row[self.FONTE_RECURSO], row[self.FONTE_RECURSO_NOME]),
                    esfera_orcamentaria=self.get_esfera_orcamentaria(row[self.ESFERA_ORCAMENTARIA], row[self.ESFERA_ORCAMENTARIA_NOME]),
                    emitente_ug=self.get_unidade_gestora(row[self.EXECUTORA_UG], row[self.EXECUTORA_UG_NOME]),
                    responsavel_ug=self.get_unidade_gestora(row[self.RESPONSAVEL_UG], row[self.RESPONSAVEL_UG_NOME]),
                    acao_governo_original=row[self.ACAO_GOVERNO],
                    fonte_recurso_original=row[self.FONTE_RECURSO],
                    naturesa_despesa_original=row[self.NATUREZA_DESPESA],
                    grupo_despesa_original=row[self.GRUPO_DESPESA],
                ),
            )
            documento.tipo = tipo
            if tipo in [DocumentoBase.TIPO_NE, DocumentoBase.TIPO_RO]:
                documento.documento_empenho_inicial = self._cache.get_item('documento', numero_ne)

            documento.save()
            if created:
                self.log(u'Criando Documento: {}\n'.format(numero_documento))
            else:
                self.log(u'Atualizando Documento: {}\n'.format(numero_documento))

            self._cache.add_item('documento', numero_documento, documento)

        return documento

    def processar_documento_item(self, row):
        numero_ne = row[self.NE]
        numero_documento = row[self.DOCUMENTO]
        natureza_despesa = self.get_natureza_despesa(row[self.NATUREZA_DESPESA], row[self.NATUREZA_DESPESA_NOME])
        subitem = self.get_subitem_natureza_despesa(natureza_despesa, row[self.SUBITEM], row[self.SUBITEM_NOME])

        self.log(u'Adicionando Documento {} da Nota de Empenho: {}\n'.format(numero_documento, numero_ne))
        tipo = self.get_tipo(numero_documento)
        ClasseDocumento = self.get_documento_classe(tipo)
        documento = self._cache.get_item('documento', numero_documento)
        if documento is None:
            documento = ClasseDocumento.objects.get(numero=numero_documento)

        if tipo in [DocumentoBase.TIPO_NE, DocumentoBase.TIPO_RO]:
            valor = self.get_valor(row[self.DESPESAS_EMPENHADAS])
            ClasseDocumentoItem = DocumentoEmpenhoItem
            kwargs = dict(documento_empenho=documento, subitem=subitem)
        elif tipo == DocumentoBase.TIPO_NS:
            valor = self.get_valor(row[self.DESPESAS_LIQUIDADAS])
            ClasseDocumentoItem = DocumentoLiquidacaoItem
            documento_empenho_inicial = self._cache.get_item('documento', numero_ne)
            kwargs = dict(documento_liquidacao=documento, subitem=subitem, documento_empenho_inicial=documento_empenho_inicial)
        else:
            valor = self.get_valor(row[self.DESPESAS_PAGAS])
            ClasseDocumentoItem = DocumentoPagamentoItem
            documento_empenho_inicial = self._cache.get_item('documento', numero_ne)
            kwargs = dict(documento_pagamento=documento, subitem=subitem, documento_empenho_inicial=documento_empenho_inicial)

        documento_item = ClasseDocumentoItem.objects.filter(**kwargs)
        if documento_item.exists():
            self.log(u'Atualizando item do Documento: {}\n'.format(numero_documento))
            documento_item = documento_item[0]
        else:
            self.log(u'Criando item do Documento: {}\n'.format(numero_documento))
            documento_item = ClasseDocumentoItem(**kwargs)
            documento_item.valor = valor

        documento_item.subitem_original = row[self.SUBITEM]
        documento_item.save()

    def iterar(self, rows):
        ne_ro = dict()
        for row in rows:
            numero_ne = row[self.NE]
            numero_documento = row[self.DOCUMENTO]
            ano_emissao = row[self.ANO_EMICAO]
            if ano_emissao < '2021':
                if numero_ne == numero_documento:
                    self.processar_documento(row)
            else:
                tipo = self.get_tipo(numero_documento)
                if tipo == DocumentoBase.TIPO_RO:
                    if numero_ne not in ne_ro:
                        ne_ro[numero_ne] = list()
                    ne_ro[numero_ne].append(row)

        # Trata a primeira RO como Empenho inicial
        for numero_ne, ro_rows in ne_ro.items():
            ro_rows = sorted(ro_rows, key=lambda row: row[self.DOCUMENTO])
            ro_rows = sorted(ro_rows, key=lambda row: row[self.DT_EMICAO])
            empenho_row = ro_rows[0].copy()
            empenho_row[self.DOCUMENTO] = empenho_row[self.NE]
            empenho_row[self.DESPESAS_EMPENHADAS] = 0
            self.processar_documento(empenho_row)
            self.processar_documento_item(empenho_row)

        for row in rows:
            numero_ne = row[self.NE]
            numero_documento = row[self.DOCUMENTO]
            if numero_ne != numero_documento:
                self.processar_documento(row)

        self.log(u'\nInserindo itens dos documentos\n')
        for row in rows:
            self.processar_documento_item(row)


class ImportadorRAP(Importador):
    EXECUTORA_UG = 0
    EXECUTORA_UG_NOME = 1
    RESPONSAVEL_UG = 2
    RESPONSAVEL_UG_NOME = 3
    UNIDADE_ORCAMENTARIA = 4
    UNIDADE_ORCAMENTARIA_NOME = 5
    ACAO_GOVERNO = 6
    ACAO_GOVERNO_NOME = 7
    PTRES = 8
    PI = 9
    PI_NOME = 10
    ANO_LANCAMENTO = 11
    ANO_EMICAO = 12
    NE = 13
    NATUREZA_DESPESA = 14
    NATUREZA_DESPESA_NOME = 15
    SUBITEM = 16
    SUBITEM_NOME = 17
    GRUPO_DESPESA = 18
    GRUPO_DESPESA_NOME = 19
    FONTE_RECURSO = 20
    FONTE_RECURSO_NOME = 21

    RAP_PROC_INSCRITOS = 22
    RAP_PROC_REINSCRITOS = 23
    RAP_PROC_CANCELADOS = 24
    RAP_PROC_PAGOS = 25
    RAP_N_PROC_INSCRITOS = 26
    RAP_N_PROC_REINSCRITOS = 27
    RAP_N_PROC_CANCELADOS = 28
    RAP_N_PROC_LIQUIDADOS = 29
    RAP_N_PROC_PAGOS = 30

    def __init__(self, *args, **kwargs):
        super(ImportadorRAP, self).__init__(*args, **kwargs)
        self.ini_row = 5
        self.delimiter = '\t'

        self.stdout = open(self.log_nome_arquivo, 'a') if self.tipo_log == self.LOG_ARQUIVO else sys.stdout
        self.stdout.write('\n\n')
        self.stdout.write('ImportadorRAP')

    def processar(self, row):
        numero_ne = row[self.NE]
        rap = self._cache.get_item('rap', numero_ne)
        if rap is None:
            rap, created = RAP.objects.update_or_create(
                numero=numero_ne,
                ano=row[self.ANO_LANCAMENTO],
                defaults=dict(
                    unidade_orcamentaria=self.get_classificacao_institucional(row[self.UNIDADE_ORCAMENTARIA], row[self.UNIDADE_ORCAMENTARIA_NOME]),
                    acao_governo=self.get_acao_governo(row[self.ACAO_GOVERNO], row[self.ACAO_GOVERNO_NOME]),
                    ptres=self.get_ptres(codigo=row[self.PTRES]),
                    plano_interno=self.get_plano_interno(row[self.PI], row[self.PI_NOME]),
                    fonte_recurso=self.get_fonte_recurso(row[self.FONTE_RECURSO], row[self.FONTE_RECURSO_NOME]),
                    emitente_ug=self.get_unidade_gestora(row[self.EXECUTORA_UG], row[self.EXECUTORA_UG_NOME]),
                    responsavel_ug=self.get_unidade_gestora(row[self.RESPONSAVEL_UG], row[self.RESPONSAVEL_UG_NOME]),
                    acao_governo_original=row[self.ACAO_GOVERNO],
                    fonte_recurso_original=row[self.FONTE_RECURSO],
                    naturesa_despesa_original=row[self.NATUREZA_DESPESA],
                    grupo_despesa_original=row[self.GRUPO_DESPESA],
                ),
            )
            if created:
                self.log(u'Criando RAP: {}\n'.format(numero_ne))
            else:
                self.log(u'Atualizando RAP: {}\n'.format(numero_ne))

            self._cache.add_item('rap', numero_ne, rap)

        natureza_despesa = self.get_natureza_despesa(row[self.NATUREZA_DESPESA], row[self.NATUREZA_DESPESA_NOME])
        subitem = self.get_subitem_natureza_despesa(natureza_despesa, row[self.SUBITEM], row[self.SUBITEM_NOME])
        rap_item, created = RAPItem.objects.update_or_create(
            rap=rap,
            subitem=subitem,
            subitem_original=row[self.SUBITEM],
            defaults=dict(
                valor_proc_inscrito=self.get_valor(row[self.RAP_PROC_INSCRITOS]),
                valor_proc_reinscrito=self.get_valor(row[self.RAP_PROC_REINSCRITOS]),
                valor_proc_cancelado=self.get_valor(row[self.RAP_PROC_CANCELADOS]),
                valor_proc_pago=self.get_valor(row[self.RAP_PROC_PAGOS]),
                valor_nao_proc_inscrito=self.get_valor(row[self.RAP_N_PROC_INSCRITOS]),
                valor_nao_proc_reinscrito=self.get_valor(row[self.RAP_N_PROC_REINSCRITOS]),
                valor_nao_proc_cancelado=self.get_valor(row[self.RAP_N_PROC_CANCELADOS]),
                valor_nao_proc_liquidado=self.get_valor(row[self.RAP_N_PROC_LIQUIDADOS]),
                valor_nao_proc_pago=self.get_valor(row[self.RAP_N_PROC_PAGOS]),
            ),
        )
        if created:
            self.log(u'Criando item do RAP: {}\n'.format(numero_ne))
        else:
            self.log(u'Atualizando item do RAP: {}\n'.format(numero_ne))


class ImportadorGRU(Importador):
    EXECUTORA_UG = 0
    EXECUTORA_UG_NOME = 1
    GRU = 2
    GRU_NOME = 3
    ANO_LANCAMENTO = 4
    VALOR = 5

    def __init__(self, *args, **kwargs):
        super(ImportadorGRU, self).__init__(*args, **kwargs)
        self.ini_row = 8
        self.delimiter = '\t'

        self.stdout = open(self.log_nome_arquivo, 'a') if self.tipo_log == self.LOG_ARQUIVO else sys.stdout
        self.stdout.write('\n\n')
        self.stdout.write('ImportadorGRU')

    def processar(self, row):
        executora = row[self.EXECUTORA_UG]
        gru = row[self.GRU]
        identificador = f'{executora}-{gru}'
        receita_gru = self._cache.get_item('receita_gru', identificador)
        if receita_gru is None:
            receita_gru, created = ReceitaGRU.objects.update_or_create(
                emitente_ug=self.get_unidade_gestora(executora, row[self.EXECUTORA_UG_NOME]),
                gru=self.get_gru(gru, row[self.GRU_NOME]),
                ano=row[self.ANO_LANCAMENTO],
                defaults=dict(valor=self.get_valor(row[self.VALOR])),
            )
            if created:
                self.log(u'Criando ReceitaGRU: {}\n'.format(identificador))
            else:
                self.log(u'Atualizando ReceitaGRU: {}\n'.format(identificador))

            self._cache.add_item('rap', identificador, receita_gru)
