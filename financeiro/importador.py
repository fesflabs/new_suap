# -*- coding: utf-8 -*-

from datetime import datetime
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.utils.termcolors import colorize

from comum.models import Vinculo
from djtools.utils import mask_cnpj, mask_cpf
from financeiro.models import (
    ClassificacaoDespesa,
    ProgramaTrabalho,
    Localizacao,
    CategoriaEconomicaDespesa,
    NaturezaDespesa,
    GrupoNaturezaDespesa,
    ModalidadeAplicacao,
    Programa,
    Acao,
    Subfuncao,
    Funcao,
    NEListaItens,
    NEItem,
    SubElementoNaturezaDespesa,
    Evento,
    InstrumentoLegal,
    EsferaOrcamentaria,
    ProgramaTrabalhoResumido,
    ClassificacaoInstitucional,
    ModalidadeLicitacao,
    PlanoInterno,
    ElementoDespesa,
    FonteRecurso,
    GrupoFonteRecurso,
    EspecificacaoFonteRecurso,
    LogImportacaoSIAFI,
    NotaCreditoItem,
    NotaDotacao,
    IdentificadorResultadoPrimario,
    NotaCredito,
    NotaDotacaoItem,
    NotaSistema,
    NotaSistemaItem,
)
from operator import itemgetter
import gzip
import os
from django.apps import apps

from rh.models import PessoaJuridicaContato, PessoaExterna

Pessoa = apps.get_model('rh', 'pessoa')
PessoaJuridica = apps.get_model('rh', 'pessoajuridica')
PessoaTelefone = apps.get_model('comum', 'pessoatelefone')
PessoaEndereco = apps.get_model('comum', 'pessoaendereco')
PessoaFisica = apps.get_model('rh', 'pessoafisica')
Funcionario = apps.get_model('rh', 'funcionario')
Municipio = apps.get_model('comum', 'municipio')
NotaEmpenho = apps.get_model('financeiro', 'notaempenho')
UnidadeGestora = apps.get_model('financeiro', 'unidadegestora')

FINANCEIRO_ARQUIVOS = os.path.join(settings.BASE_DIR, 'financeiro/arquivos')
FINANCEIRO_ARQUIVOS_PROCESSADOS = os.path.join(settings.BASE_DIR, 'financeiro/arquivos/processados')


def identificar_layout(arquivo_ref_path):
    """
    Com base no ``arquivo_ref_path`` identifica o layout na base de layouts em 
    financeiro/refs.
    """
    arquivo = open(arquivo_ref_path, 'r')
    conteudo = arquivo.read()
    arquivo.close()
    arquivos_ref_path = os.path.join(settings.BASE_DIR, 'financeiro/refs')
    for arquivo_nome_ref in [i for i in os.listdir(arquivos_ref_path) if i.endswith('.ref')]:
        arquivo_ref = open(os.path.join(arquivos_ref_path, arquivo_nome_ref), 'r')
        conteudo_ref = arquivo_ref.read()
        arquivo_ref.close()
        if conteudo.strip().replace('\n', '').replace('\t', '').replace('\r', '').replace(' ', '') == conteudo_ref.strip().replace('\n', '').replace('\t', '').replace(
            '\r', ''
        ).replace(' ', ''):
            return arquivo_nome_ref.replace('.ref', '')


def descompactar_arquivos(path):
    """Descompacta os arquivos com extensão .gz"""
    for filename in [i for i in os.listdir(path) if i.endswith('.gz')]:
        gzip_file_path = os.path.join(path, filename)
        try:
            gzip_file = gzip.open(gzip_file_path, 'rb')
            content = gzip_file.read()
        except IOError:
            gzip_file.close()
            os.remove(gzip_file_path)
            print((colorize('Arquivo corrompido: %s' % filename, fg='white', bg='red')))
            continue
        file_ = open(os.path.join(path, filename.replace('.gz', '')), 'w')
        file_.write(content)
        gzip_file.close()
        os.remove(gzip_file_path)
        file_.close()


def get_ref_info(arquivo_ref_conteudo):
    info = dict()
    posicao = 1
    for i in arquivo_ref_conteudo:
        descricao, tipo, tamanho = i.split()
        tamanho_int = sum([int(n) for n in tamanho.split(',')])
        info[descricao] = dict(tipo=tipo, tamanho=i[41:].strip(), tamanho_int=tamanho_int, inicio=posicao - 1, fim=posicao + tamanho_int - 1)  # tamanho puro
        posicao = posicao + tamanho_int
    return info


def get_item(linha, ref_info):
    item = dict()
    for campo_nome, campo_info in list(ref_info.items()):
        valor = linha[campo_info['inicio']: campo_info['fim']].strip()
        if not valor.replace('0', ''):
            valor = None
        elif '-DA-' in campo_nome and campo_info['tamanho_int'] == 8:
            formato = '%Y%m%d'
            mes_formato_YMD = int(valor[4:6])
            if mes_formato_YMD in (19, 20):
                formato = '%d%m%Y'
            try:
                valor = datetime.strptime(valor, formato)
            except ValueError:
                valor = None
        item[campo_nome] = valor
    return item


def get_itens(ref_filename, txt_filename, order_by=None):
    ref_file = open(ref_filename, 'r')
    ref_linhas = ref_file.readlines()
    ref_file.close()
    txt_file = open(txt_filename, 'r')
    txt_linhas = txt_file.readlines()
    txt_file.close()
    itens = []
    ref_info = get_ref_info(ref_linhas)
    largura_esperada = sum([i['tamanho_int'] for i in list(ref_info.values())])
    largura_recebida = len(txt_linhas[0].decode('latin-1').replace('\n', '').replace('\t', '').replace('\r', ''))
    if largura_esperada != largura_recebida:
        print((colorize('Largura REF e TXT incompatível (esperado: %s; recebido: %s)' % (largura_esperada, largura_recebida), fg='red')))
        return []
    for linha in txt_linhas:
        linha = linha.decode('latin-1').replace('\n', '').replace('\t', '').replace('\r', '')
        item = get_item(linha, ref_info)
        for key, value in list(item.items()):  # Insere campo -DAHO- caso tenha campos -DA- e -HO- compatíveis
            eh_campo_hora = '-HO-' in key and ref_info[key]['tamanho_int'] == 4
            campo_data_nome = key.replace('-HO-', '-DA-')
            tem_campo_data = campo_data_nome in item
            if eh_campo_hora and tem_campo_data and item[campo_data_nome]:
                nome_campo_daho = key.replace('-HO-', '-DAHO-')
                item[nome_campo_daho] = datetime.strptime(item[campo_data_nome].strftime('%Y%m%d') + (value or '0000'), '%Y%m%d%H%M')
        itens.append(item)
    if order_by:
        itens = sorted(itens, key=itemgetter(order_by))
    return itens


def formata_decimal(valor):
    return valor[:-2] + '.' + valor[-2:]


def formata_decimal_casas_decimais(valor, n_casas_decimais):
    return Decimal(valor[:-n_casas_decimais] + '.' + valor[-n_casas_decimais:])


def get_or_create_programa_trabalho(cod_programa_trabalho):
    try:
        p_trabalho = ProgramaTrabalho.objects.get(codigo=cod_programa_trabalho)
    except ProgramaTrabalho.DoesNotExist:
        # divide o codigo de programa de trabalho nas partes que compoem a entidade
        _funcao = cod_programa_trabalho[0:2]
        _subfuncao = cod_programa_trabalho[2:5]
        _acao = cod_programa_trabalho[5:13]
        _localizacao = cod_programa_trabalho[13:]

        try:
            funcao = Funcao.objects.get(codigo=_funcao)
        except Funcao.DoesNotExist:
            funcao = Funcao(codigo=_funcao, nome='%s: Sem nome' % _funcao)
            funcao.save()

        try:
            subfuncao = Subfuncao.objects.get(codigo=_subfuncao)
        except Subfuncao.DoesNotExist:
            subfuncao = Subfuncao(codigo=_subfuncao, nome='%s: Sem nome' % _subfuncao)
            subfuncao.save()

        try:
            acao = Acao.objects.get(codigo=_acao)
        except Acao.DoesNotExist:
            c_programa = _acao[0:4]

            try:
                programa = Programa.objects.get(codigo=c_programa)
            except Programa.DoesNotExist:
                programa = Programa(codigo=c_programa, nome='%s: Sem nome' % c_programa)
                programa.save()

            c_acao = _acao[4:]
            acao = Acao(codigo_acao=c_acao, nome='%s: Sem nome' % _acao, programa=programa)
            acao.save()

        try:
            localizacao = Localizacao.objects.get(codigo=_localizacao)
        except Localizacao.DoesNotExist:
            localizacao = Localizacao(codigo=_localizacao, nome='%s: Sem nome' % _localizacao)
            localizacao.save()

        # cria o objeto programa de trabalho
        p_trabalho = ProgramaTrabalho(funcao=funcao, subfuncao=subfuncao, acao=acao, localizacao=localizacao)
        p_trabalho.save()

    return p_trabalho


def get_or_create_classificacao_despesa(codigo):
    try:
        c_despesa = ClassificacaoDespesa.objects.get(codigo=codigo)
    except ClassificacaoDespesa.DoesNotExist:
        c_despesa = ClassificacaoDespesa(codigo=codigo, nome='Não informado')
        c_despesa.save()

    return c_despesa


def get_or_create_natureza_despesa(cod_natureza_despesa):
    try:
        natureza_despesa = NaturezaDespesa.objects.get(codigo=cod_natureza_despesa)
    except NaturezaDespesa.DoesNotExist:
        natureza_despesa = NaturezaDespesa(codigo=cod_natureza_despesa, nome=cod_natureza_despesa)

        try:
            categoria = CategoriaEconomicaDespesa.objects.get(codigo=cod_natureza_despesa[0:1])
        except CategoriaEconomicaDespesa.DoesNotExist:
            categoria = CategoriaEconomicaDespesa(codigo=cod_natureza_despesa[0:1], nome=cod_natureza_despesa[0:1], descricao='')
            categoria.save()

        try:
            grupo = GrupoNaturezaDespesa.objects.get(codigo=cod_natureza_despesa[1:2])
        except GrupoNaturezaDespesa.DoesNotExist:
            grupo = GrupoNaturezaDespesa(codigo=cod_natureza_despesa[1:2], nome=cod_natureza_despesa[1:2], descricao='')
            grupo.save()

        try:
            modalidade = ModalidadeAplicacao.objects.get(codigo=cod_natureza_despesa[2:4])
        except ModalidadeAplicacao.DoesNotExist:
            modalidade = ModalidadeAplicacao(codigo=cod_natureza_despesa[2:4], nome=cod_natureza_despesa[2:4], descricao='')
            modalidade.save()

        try:
            elemento = ElementoDespesa.objects.get(codigo=cod_natureza_despesa[4:])
        except ElementoDespesa.DoesNotExist:
            elemento = ElementoDespesa(codigo=cod_natureza_despesa[4:], nome=cod_natureza_despesa[4:], descricao='')
            elemento.save()

        natureza_despesa.categoria_economica_despesa = categoria
        natureza_despesa.grupo_natureza_despesa = grupo
        natureza_despesa.modalidade_aplicacao = modalidade
        natureza_despesa.elemento_despesa = elemento

        natureza_despesa.save()

    return natureza_despesa


def get_or_create_fonte_recurso(cod_fonte_recurso):
    try:
        fonte_recurso = FonteRecurso.objects.get(codigo=cod_fonte_recurso)
    except FonteRecurso.DoesNotExist:
        fonte_recurso = FonteRecurso(codigo=cod_fonte_recurso)

        try:
            grupo = GrupoFonteRecurso.objects.get(codigo=cod_fonte_recurso[0:1])
        except GrupoFonteRecurso.DoesNotExist:
            grupo = GrupoFonteRecurso(codigo=cod_fonte_recurso[0:1])
            grupo.nome = cod_fonte_recurso[0:1]
            grupo.save()

        try:
            especificacao = EspecificacaoFonteRecurso.objects.get(codigo=cod_fonte_recurso[1:])
        except EspecificacaoFonteRecurso.DoesNotExist:
            especificacao = EspecificacaoFonteRecurso(codigo=cod_fonte_recurso[1:])
            especificacao.nome = cod_fonte_recurso[1:]
            especificacao.save()

        fonte_recurso.nome = cod_fonte_recurso
        fonte_recurso.grupo = grupo
        fonte_recurso.especificacao = especificacao

        fonte_recurso.save()

    return fonte_recurso


def get_or_create_esfera_orcamentaria(cod_esfera_orcamentaria):
    try:
        esfera_orcamentaria = EsferaOrcamentaria.objects.get(codigo=cod_esfera_orcamentaria)
    except EsferaOrcamentaria.DoesNotExist:
        # é provável que não seja necessário criar novas esferas orçamentárias ja que a tabela foi alimentada pelo MTO
        esfera_orcamentaria = EsferaOrcamentaria(codigo=cod_esfera_orcamentaria, nome=cod_esfera_orcamentaria)
        esfera_orcamentaria.save()

    return esfera_orcamentaria


def get_or_create_evento(cod_evento):
    try:
        evento = Evento.objects.get(codigo=cod_evento)
    except Evento.DoesNotExist:
        evento = Evento(codigo=cod_evento, nome=cod_evento)
        evento.save()

    return evento


def get_or_create_instrumento_legal(codigo):
    try:
        instrumento = InstrumentoLegal.objects.get(codigo=codigo)
    except InstrumentoLegal.DoesNotExist:
        instrumento = InstrumentoLegal(codigo=codigo, nome=codigo)
        instrumento.save()

    return instrumento


def get_or_create_unidade_gestora(cod_unidade_gestora):
    try:
        unidade_gestora = UnidadeGestora.objects.get(codigo=cod_unidade_gestora)
    except UnidadeGestora.DoesNotExist:
        unidade_gestora = UnidadeGestora(codigo=cod_unidade_gestora, nome=cod_unidade_gestora)
        unidade_gestora.save()

    return unidade_gestora


def get_or_create_classificacao_institucional(cod_classificacao_institucional):
    try:
        classificacao_institucional = ClassificacaoInstitucional.objects.get(codigo=cod_classificacao_institucional)
    except ClassificacaoInstitucional.DoesNotExist:
        classificacao_institucional = ClassificacaoInstitucional(codigo=cod_classificacao_institucional, nome=cod_classificacao_institucional)
        classificacao_institucional.save()

    return classificacao_institucional


def get_or_create_ptres(cod_ptres):
    try:
        ptres = ProgramaTrabalhoResumido.objects.get(codigo=cod_ptres)
    except ProgramaTrabalhoResumido.DoesNotExist:
        ptres = ProgramaTrabalhoResumido(codigo=cod_ptres)
        ptres.save()

    return ptres


def get_or_create_plano_interno(cod_plano):
    try:
        plano_interno = PlanoInterno.objects.get(codigo=cod_plano)
    except PlanoInterno.DoesNotExist:
        plano_interno = PlanoInterno(codigo=cod_plano)
        plano_interno.save()

    return plano_interno


def get_or_create_modalidade_licitacao(cod_modalidade):
    try:
        modalidade = ModalidadeLicitacao.objects.get(codigo=cod_modalidade)
    except ModalidadeLicitacao.DoesNotExist:
        modalidade = ModalidadeLicitacao(codigo=cod_modalidade)
        modalidade.save()

    return modalidade


def get_or_none_nota_empenho(cod_emitente, numero):
    try:
        empenho = NotaEmpenho.objects.get(emitente_ug__codigo=cod_emitente, numero=numero)
    except NotaEmpenho.DoesNotExist:
        empenho = None

    return empenho


def get_or_none_lista_itens_empenho(numero_original):
    try:
        lista = NEListaItens.objects.get(numero_original=numero_original)
    except NEListaItens.DoesNotExist:
        lista = None

    return lista


def importar_municipios(nome_arquivo_ref, nome_arquivo_txt):
    itens = get_itens(nome_arquivo_ref, nome_arquivo_txt)
    for i in itens:
        m, created = Municipio.get_or_create(i['IT-NO-MUNICIPIO'], i['IT-CO-UF'])
        if created:
            m.nome = i['IT-NO-MUNICIPIO']
            m.uf = i['IT-CO-UF']
        m.codigo = i['IT-CO-MUNICIPIO']
        m.save()


@transaction.atomic
def importar_credores(nome_arquivo_ref, nome_arquivo_txt):
    """
    Importa os CREDORES do SIAFI para as classes PessoaFisica ou PessoaJuridica 
    e PessoaTelefone e PessoaEndereco.
    """
    print('>>> importar_credores')

    funcionarios_cpfs = set(Funcionario.objects.order_by('cpf').values_list('cpf', flat=True))
    cpfs_existentes = set(PessoaFisica.objects.order_by('cpf').values_list('cpf', flat=True))

    for i in get_itens(nome_arquivo_ref, nome_arquivo_txt):

        if len(i['IT-CO-CREDOR']) == 14:  # pessoa jurídica
            cnpj = mask_cnpj(i['IT-CO-CREDOR'])
            pk = PessoaJuridica.objects.get_or_create(cnpj=cnpj)[0].pk

        elif len(i['IT-CO-CREDOR']) == 11:  # pessoa física
            cpf = mask_cpf(i['IT-CO-CREDOR'])

            # Caso a pessoa já seja um funcionário do SUAP, assume-se
            # que a informação do SIAPE é mais recente que a SIAFI
            if cpf in funcionarios_cpfs:
                continue

            # Tratamento porque temos CPFs duplicados em PessoaFisica
            if cpf in cpfs_existentes:
                pk = PessoaFisica.objects.filter(cpf=cpf).values_list('pk', flat=True).latest('pk')
            else:
                pk = PessoaFisica.objects.create(cpf=cpf).pk

        else:
            print(('ERRO:', i))

        Pessoa.objects.filter(pk=pk).update(
            nome=i['IT-NO-CREDOR'], nome_usual=i['IT-NO-MNEMONICO-CREDOR'], natureza_juridica=i['IT-CO-NATUREZA-JURIDICA'] or '', sistema_origem='SIAFI'
        )

        # Tratando os telefones
        PessoaJuridicaContato.objects.filter(pessoa_juridica__pessoa_ptr__id=pk).delete()
        if i['IT-NU-TELEFONE-CREDOR']:
            PessoaJuridicaContato.objects.create(pessoa_juridica__pessoa_ptr__id=pk, descricao='Telefone', telefone=i['IT-NU-TELEFONE-CREDOR'])

        # Endereço
        PessoaEndereco.objects.filter(pessoa__id=pk).delete()
        m, created = Municipio.objects.get_or_create(codigo=i['IT-CO-MUNICIPIO-CREDOR'])
        PessoaEndereco.objects.create(pessoa_id=pk, municipio=m, logradouro=i['IT-ED-CREDOR'], cep=i['IT-CO-CEP-CREDOR'])


def importar_eventos(nome_arquivo_ref, nome_arquivo_txt):
    itens = get_itens(nome_arquivo_ref, nome_arquivo_txt)
    for i in itens:
        if i['GR-CODIGO-EVENTO']:
            codigo = i['GR-CODIGO-EVENTO']
            nome = i['IT-NO-EVENTO']
            descricao = i['IT-TX-DESCRICAO-EVENTO']

            try:
                evento = Evento.objects.get(codigo=codigo)
            except Evento.DoesNotExist:
                evento = Evento(codigo=codigo)

            evento.nome = nome
            evento.descricao = descricao

            if i['IT-IN-OPERACAO']:
                if i['IT-IN-OPERACAO'] == 'E':
                    evento.ativo = False
                elif i['IT-IN-OPERACAO'] == 'R':
                    evento.ativo = True

            evento.save()
    return


def importar_unidades_gestoras(nome_arquivo_ref, nome_arquivo_txt):
    itens = get_itens(nome_arquivo_ref, nome_arquivo_txt)
    for i in itens:
        try:
            ug = UnidadeGestora.objects.get(codigo=i['IT-CO-UNIDADE-GESTORA'])
        except UnidadeGestora.DoesNotExist:
            ug = UnidadeGestora(codigo=i['IT-CO-UNIDADE-GESTORA'])

        if i['IT-CO-MUNICIPIO']:
            try:
                municipio = Municipio.objects.get(codigo=i['IT-CO-MUNICIPIO'])
            except Municipio.DoesNotExist:
                municipio = None
        else:
            municipio = None

        ug.municipio = municipio
        ug.nome = i['IT-NO-UNIDADE-GESTORA']
        ug.mnemonico = i['IT-NO-MNEMONICO-UNIDADE-GESTORA']
        if i['IT-IN-FUNCAO-UG'] == '1':
            ug.funcao = 'Executora'
        elif i['IT-IN-FUNCAO-UG'] == '2':
            ug.funcao = 'Credora'
        else:
            ug.funcao = 'Controle'
        ug.ativo = i['IT-IN-ATIVO'] != 'I'
        ug.save()


def importar_ptres(nome_arquivo_ref, nome_arquivo_txt):
    itens = get_itens(nome_arquivo_ref, nome_arquivo_txt, 'IT-DA-TRANSACAO')
    for i in itens:
        if i['IT-CO-PROGRAMA-TRABALHO-RESUMIDO']:
            codigo = i['IT-CO-PROGRAMA-TRABALHO-RESUMIDO']
            ptraba = i['GR-PROGRAMA-TRABALHO-A']
            un_orc = i['GR-UNIDADE-ORCAMENTARIA']
            res_pr = i['IT-IN-RESULTADO-LEI']
            tp_cre = i['IT-IN-TIPO-CREDITO']

            if not res_pr:
                res_pr = 0
            else:
                res_pr = int(res_pr)

            unidade_orc = get_or_create_classificacao_institucional(un_orc)

            try:
                resultado_p = IdentificadorResultadoPrimario.objects.get(codigo=res_pr)
            except IdentificadorResultadoPrimario.DoesNotExist:
                resultado_p = IdentificadorResultadoPrimario(codigo=res_pr, nome='%s: Sem nome' % res_pr)
                resultado_p.save()

            p_trabalho = get_or_create_programa_trabalho(ptraba)

            # cria o ptres
            try:
                ptres = ProgramaTrabalhoResumido.objects.get(codigo=codigo)

                ptres.programa_trabalho = p_trabalho
                ptres.classificacao_institucional = unidade_orc
                ptres.resultado_primario = resultado_p
                ptres.tipo_credito = tp_cre

            except ProgramaTrabalhoResumido.DoesNotExist:
                ptres = ProgramaTrabalhoResumido(
                    codigo=codigo, programa_trabalho=p_trabalho, classificacao_institucional=unidade_orc, resultado_primario=resultado_p, tipo_credito=tp_cre
                )

            if i['IT-IN-OPERACAO']:
                if i['IT-IN-OPERACAO'] == 'E':
                    ptres.ativo = False
                elif i['IT-IN-OPERACAO'] == 'R':
                    ptres.ativo = True

            ptres.save()


def importar_programas_trabalho(nome_arquivo_ref, nome_arquivo_txt):
    """essa importação é dependente da importação dos ptres, pois apenas os programas de trabalhos já associados a algum ptres serão atualizados.
        isso foi realizado por que no arquivo de extração de ptres existe apenas os programas referentes a unidade orçamentária do IFRN e deste
        modo não serão cadastrados registros de outras unidades"""
    itens = get_itens(nome_arquivo_ref, nome_arquivo_txt, 'IT-DA-OPERACAO')
    for i in itens:
        if i['GR-PROGRAMA-TRABALHO']:
            try:
                pt = ProgramaTrabalho.objects.get(codigo=i['GR-PROGRAMA-TRABALHO'])

                if i['IT-CO-MUNICIPIO-IBGE']:
                    try:
                        municipio = Municipio.objects.get(codigo=i['IT-CO-MUNICIPIO-IBGE'])
                    except Municipio.DoesNotExist:
                        municipio = None
                else:
                    municipio = None

                pt.municipio = municipio

                if i['IT-IN-OPERACAO']:
                    if i['IT-IN-OPERACAO'] == 'E':
                        pt.ativo = False
                    elif i['IT-IN-OPERACAO'] == 'R':
                        pt.ativo = True

                pt.save()
            except ProgramaTrabalho.DoesNotExist:
                continue


def importar_planos_internos(nome_arquivo_ref, nome_arquivo_txt):
    itens = get_itens(nome_arquivo_ref, nome_arquivo_txt, 'IT-DA-OPERACAO')
    for i in itens:
        if i['IT-CO-PLANO-INTERNO']:
            codigo = i['IT-CO-PLANO-INTERNO']
            nome = i['IT-NO-PLANO-INTERNO']
            objets = [
                i['IT-TX-OBJETIVO-PLANO-INTERNO(1)'],
                i['IT-TX-OBJETIVO-PLANO-INTERNO(2)'],
                i['IT-TX-OBJETIVO-PLANO-INTERNO(3)'],
                i['IT-TX-OBJETIVO-PLANO-INTERNO(4)'],
                i['IT-TX-OBJETIVO-PLANO-INTERNO(5)'],
                i['IT-TX-OBJETIVO-PLANO-INTERNO(6)'],
                i['IT-TX-OBJETIVO-PLANO-INTERNO(7)'],
                i['IT-TX-OBJETIVO-PLANO-INTERNO(8)'],
                i['IT-TX-OBJETIVO-PLANO-INTERNO(9)'],
                i['IT-TX-OBJETIVO-PLANO-INTERNO(10)'],
                i['IT-TX-OBJETIVO-PLANO-INTERNO(11)'],
                i['IT-TX-OBJETIVO-PLANO-INTERNO(12)'],
                i['IT-TX-OBJETIVO-PLANO-INTERNO(13)'],
                i['IT-TX-OBJETIVO-PLANO-INTERNO(14)'],
                i['IT-TX-OBJETIVO-PLANO-INTERNO(15)'],
                i['IT-TX-OBJETIVO-PLANO-INTERNO(16)'],
                i['IT-TX-OBJETIVO-PLANO-INTERNO(17)'],
                i['IT-TX-OBJETIVO-PLANO-INTERNO(18)'],
                i['IT-TX-OBJETIVO-PLANO-INTERNO(19)'],
                i['IT-TX-OBJETIVO-PLANO-INTERNO(20)'],
            ]
            cod_or = i['GR-ORGAO']
            un_orc = i['GR-UNIDADE-ORCAMENTARIA']
            ptraba = i['GR-PROGRAMA-TRABALHO']
            un_ges = i['IT-CO-UNIDADE-GESTORA']
            es_orc = i['IT-IN-ESFERA-ORCAMENTARIA']

            # concatena os textos do objetivo
            objetivo = ''
            for o in objets:
                if o:
                    objetivo += o

            orgao = get_or_create_classificacao_institucional(cod_or)

            if un_orc:
                unidade_orcamentaria = get_or_create_classificacao_institucional(un_orc)
            else:
                unidade_orcamentaria = None

            if un_ges:
                unidade_gestora = get_or_create_unidade_gestora(un_ges)
            else:
                unidade_gestora = None

            if es_orc:
                esfera_orcamentaria = get_or_create_esfera_orcamentaria(es_orc)
            else:
                esfera_orcamentaria = None

            if ptraba:
                programa_trabalho = get_or_create_programa_trabalho(ptraba)
            else:
                programa_trabalho = None

            # cria o ptres
            try:
                plano_interno = PlanoInterno.objects.get(codigo=codigo)

                plano_interno.nome = nome
                plano_interno.objetivo = objetivo
                plano_interno.orgao = orgao
                plano_interno.unidade_orcamentaria = unidade_orcamentaria
                plano_interno.programa_trabalho = programa_trabalho
                plano_interno.unidade_gestora = unidade_gestora
                plano_interno.esfera_orcamentaria = esfera_orcamentaria

            except PlanoInterno.DoesNotExist:
                plano_interno = PlanoInterno(
                    codigo=codigo,
                    nome=nome,
                    objetivo=objetivo,
                    orgao=orgao,
                    unidade_orcamentaria=unidade_orcamentaria,
                    programa_trabalho=programa_trabalho,
                    unidade_gestora=unidade_gestora,
                    esfera_orcamentaria=esfera_orcamentaria,
                )

            if i['IT-IN-OPERACAO']:
                if i['IT-IN-OPERACAO'] == 'E':
                    plano_interno.ativo = False
                elif i['IT-IN-OPERACAO'] == 'R':
                    plano_interno.ativo = True

            plano_interno.save()


def importar_notas_credito(nome_arquivo_ref, nome_arquivo_txt):
    itens = get_itens(nome_arquivo_ref, nome_arquivo_txt)

    # número de registros
    registros = len(itens)
    registros_naoimportados = 0

    # logs
    mensagem_log = []
    arquivo = nome_arquivo_txt.split('/')[-1]

    logs = LogImportacaoSIAFI.objects.filter(nome_arquivo=arquivo)
    if logs:
        mensagem_log.append('-- o arquivo %s já foi importado anteriormente' % arquivo)
        for linha in logs:
            mensagem_log.append('-- em %s foram %s registros não importados de %s analisados.' % (linha.data_hora.strftime("%d/%m/%Y as %H:%M:%S"), linha.nao_importados, linha.reg_analisados))

    for i in itens:
        numero = i['GR-UG-GESTAO-AN-NUMERO-NCUQ'][11:]
        numero_original = i['IT-NU-ORIGINAL']
        datahora = i['IT-DA-EMISSAO']
        emit_ug = i['GR-UG-GESTAO-AN-NUMERO-NCUQ'][0:6]
        emit_gestao = i['GR-UG-GESTAO-AN-NUMERO-NCUQ'][6:11]
        fav_ug = i['IT-CO-UG-FAVORECIDA']
        fav_gestao = i['IT-CO-GESTAO-FAVORECIDA']
        obs = i['IT-TX-OBSERVACAO']
        cambial = formata_decimal_casas_decimais(i['IT-OP-CAMBIAL'], 4) if i['IT-OP-CAMBIAL'] else None
        sistema_or = i['IT-CO-SISTEMA-ORIGEM']

        # indica se o registro já existe no sistema ou se está sendo criado agora
        created = False

        # verifica se já existe a nota de credito caso contrário cadastra
        try:
            nota_credito = NotaCredito.objects.get(numero=numero, emitente_ug__codigo=emit_ug)
        except NotaCredito.DoesNotExist:
            nota_credito = NotaCredito(numero=numero)
            created = True

        nota_credito.numero_original = numero_original
        nota_credito.datahora_emissao = datahora

        nota_credito.emitente_ci = get_or_create_classificacao_institucional(emit_gestao)
        nota_credito.emitente_ug = get_or_create_unidade_gestora(emit_ug)

        nota_credito.favorecido_ci = get_or_create_classificacao_institucional(fav_gestao)
        nota_credito.favorecido_ug = get_or_create_unidade_gestora(fav_ug)

        nota_credito.observacao = obs
        nota_credito.tx_cambial = cambial
        nota_credito.sistema_origem = sistema_or

        try:
            nota_credito.save()
        except Exception as e:
            registros_naoimportados += 1
            mensagem_log.append('-- %s não importado. erro: %s' % (numero, e))
            continue

        if created:
            # cadastra os itens da nota de credito
            for c in range(1, 21):
                if i['GR-CODIGO-EVENTO(%s)' % c]:
                    c_evento = i['GR-CODIGO-EVENTO(%s)' % c]
                    c_esfera = i['IT-IN-ESFERA-ORCAMENTARIA(%s)' % c]
                    c_ptres = i['IT-CO-PROGRAMA-TRABALHO-RESUMIDO(%s)' % c]
                    ft_rec = i['GR-FONTE-RECURSO(%s)' % c]
                    c_natdes = i['GR-NATUREZA-DESPESA(%s)' % c]
                    subitem = i['IT-CO-SUBITEM(%s)' % c]
                    c_ugr = i['IT-CO-UG-RESPONSAVEL(%s)' % c]
                    c_pti = i['IT-CO-PLANO-INTERNO(%s)' % c]
                    valor = formata_decimal(i['IT-VA-TRANSACAO(%s)' % c])

                    ptres = get_or_create_ptres(c_ptres)
                    pti = get_or_create_plano_interno(c_pti) if c_pti else None
                    ugr = get_or_create_unidade_gestora(c_ugr) if c_ugr else None

                    evento = get_or_create_evento(c_evento)
                    esfera_orcamentaria = get_or_create_esfera_orcamentaria(c_esfera)
                    fonte_recurso = get_or_create_fonte_recurso(ft_rec[1:4])
                    natureza_despesa = get_or_create_natureza_despesa(c_natdes[0:6])

                    itemNC = NotaCreditoItem(
                        nota_credito=nota_credito,
                        evento=evento,
                        esfera=esfera_orcamentaria,
                        ptres=ptres,
                        fonte_recurso=fonte_recurso,
                        fonte_recurso_original=ft_rec,
                        natureza_despesa=natureza_despesa,
                        subitem=subitem,
                        ugr=ugr,
                        plano_interno=pti,
                        valor=valor,
                    )
                    itemNC.save()

    log = LogImportacaoSIAFI(
        tipo=1, data_hora=datetime.now(), nome_arquivo=arquivo, reg_analisados=registros, nao_importados=registros_naoimportados, detalhamento='\n'.join(mensagem_log)
    )

    log.save()


def importar_notas_credito_2(nome_arquivo_ref, nome_arquivo_txt):
    """
    Esta função foi criada para tratar o novo arquivo REF nota_credito_2.ref.
    Por enquanto faz a mesma coisa da função importar_notas_credito, mas futuramente 
    os campos adicionais deverão ser tratados.
    A diferença entre os layout é o tamanho de IT-QT-LANCAMENTO.
    """
    importar_notas_credito(nome_arquivo_ref, nome_arquivo_txt)


def importar_notas_dotacao(nome_arquivo_ref, nome_arquivo_txt):
    itens = get_itens(nome_arquivo_ref, nome_arquivo_txt)

    # número de registros
    registros = len(itens)
    registros_naoimportados = 0

    # logs
    mensagem_log = []
    arquivo = nome_arquivo_txt.split('/')[-1]

    logs = LogImportacaoSIAFI.objects.filter(nome_arquivo=arquivo)
    if logs:
        mensagem_log.append('-- o arquivo %s já foi importado anteriormente' % arquivo)
        for linha in logs:
            mensagem_log.append('-- em %s foram %s registros não importados de %s analisados.' % (linha.data_hora.strftime("%d/%m/%Y as %H:%M:%S"), linha.nao_importados, linha.reg_analisados))

    for i in itens:
        numero = i['GR-UG-GESTAO-AN-NUMERO-NDUQ'][11:]
        emissao = i['IT-DA-EMISSAO']
        publicacao = i['IT-DA-PUBLICACAO']
        c_inst_legal = i['IT-CO-INSTRUMENTO-LEGAL'] if i['IT-CO-INSTRUMENTO-LEGAL'] else '0'
        n_inst_legal = i['IT-NU-INSTRUMENTO-LEGAL']
        c_nota_dotacao = i['IT-IN-NOTA-DOTACAO']
        emit_ug = i['GR-UG-GESTAO-AN-NUMERO-NDUQ'][0:6]
        emit_gestao = i['GR-UG-GESTAO-AN-NUMERO-NDUQ'][6:11]
        fav_ug = i['IT-CO-UG-FAVORECIDA']
        fav_gestao = i['IT-CO-GESTAO-FAVORECIDA']
        obs = i['IT-TX-OBSERVACAO']
        cambial = formata_decimal_casas_decimais(i['IT-OP-CAMBIAL'], 4) if i['IT-OP-CAMBIAL'] else None
        det_modalidade = i['IT-IN-DETALHAMENTO-MODALIDADE']
        det_especie = i['IT-IN-ESPECIE-DETALHAMENTO']

        # indica se o registro já existe no sistema ou se está sendo criado agora
        created = False

        # verifica se já existe a nota de credito caso contrário cadastra
        try:
            nota_dotacao = NotaDotacao.objects.get(numero=numero, emitente_ug__codigo=emit_ug)
        except NotaDotacao.DoesNotExist:
            nota_dotacao = NotaDotacao(numero=numero)
            created = True

        nota_dotacao.datahora_emissao = emissao
        nota_dotacao.datahora_publicacao = publicacao
        nota_dotacao.instrumento_legal = get_or_create_instrumento_legal(c_inst_legal)
        nota_dotacao.num_instrumento_legal = n_inst_legal
        nota_dotacao.nota_dotacao = c_nota_dotacao
        nota_dotacao.emitente_ci = get_or_create_classificacao_institucional(emit_gestao)
        nota_dotacao.emitente_ug = get_or_create_unidade_gestora(emit_ug)
        nota_dotacao.favorecido_ci = get_or_create_classificacao_institucional(fav_gestao) if fav_gestao else None
        nota_dotacao.favorecido_ug = get_or_create_unidade_gestora(fav_ug) if fav_ug else None
        nota_dotacao.observacao = obs
        nota_dotacao.tx_cambial = cambial
        nota_dotacao.detalhamento_modalidade = det_modalidade
        nota_dotacao.detalhamento_especie = det_especie

        try:
            nota_dotacao.save()
        except Exception as e:
            registros_naoimportados += 1
            mensagem_log.append('-- %s não importado. erro: %s' % (numero, e))
            continue

        if created:
            # cadastra os itens da nota de credito
            for c in range(1, 21):
                if i['GR-CODIGO-EVENTO(%s)' % c]:
                    c_evento = i['GR-CODIGO-EVENTO(%s)' % c]
                    c_esfera = i['IT-IN-ESFERA-ORCAMENTARIA(%s)' % c]
                    c_ptres = i['IT-CO-PROGRAMA-TRABALHO-RESUMIDO(%s)' % c]
                    ft_rec = i['GR-FONTE-RECURSO(%s)' % c]
                    c_natdes = i['GR-NATUREZA-DESPESA(%s)' % c]
                    c_ugr = i['IT-CO-UG-RESPONSAVEL(%s)' % c]
                    c_pti = i['IT-CO-PLANO-INTERNO(%s)' % c]
                    idoc = i['IT-CO-IDOC(%s)' % c]
                    resultado = i['IT-IN-RESULTADO(%s)' % c]
                    credito = i['IT-IN-TIPO-CREDITO(%s)' % c]
                    subitem = i['IT-CO-SUBITEM(%s)' % c]
                    valor = formata_decimal(i['IT-VA-TRANSACAO(%s)' % c])

                    ptres = get_or_create_ptres(c_ptres)
                    pti = get_or_create_plano_interno(c_pti) if c_pti else None
                    ugr = get_or_create_unidade_gestora(c_ugr) if c_ugr else None

                    evento = get_or_create_evento(c_evento)
                    esfera_orcamentaria = get_or_create_esfera_orcamentaria(c_esfera)
                    fonte_recurso = get_or_create_fonte_recurso(ft_rec[1:4])
                    natureza_despesa = get_or_create_natureza_despesa(c_natdes[0:6])

                    itemND = NotaDotacaoItem(
                        nota_dotacao=nota_dotacao,
                        evento=evento,
                        esfera=esfera_orcamentaria,
                        ptres=ptres,
                        fonte_recurso=fonte_recurso,
                        fonte_recurso_original=ft_rec,
                        natureza_despesa=natureza_despesa,
                        subitem=subitem,
                        ugr=ugr,
                        plano_interno=pti,
                        idoc=idoc,
                        resultado=resultado,
                        tipo_credito=credito,
                        valor=valor,
                    )
                    itemND.save()

    log = LogImportacaoSIAFI(
        tipo=2, data_hora=datetime.now(), nome_arquivo=arquivo, reg_analisados=registros, nao_importados=registros_naoimportados, detalhamento='\n'.join(mensagem_log)
    )
    log.save()


def importar_notas_empenho(nome_arquivo_ref, nome_arquivo_txt):
    itens = get_itens(nome_arquivo_ref, nome_arquivo_txt)

    # número de registros
    registros = len(itens)
    registros_naoimportados = 0

    # logs
    mensagem_log = []
    arquivo = nome_arquivo_txt.split('/')[-1]

    logs = LogImportacaoSIAFI.objects.filter(nome_arquivo=arquivo)
    if logs:
        mensagem_log.append('-- o arquivo %s já foi importado anteriormente' % arquivo)
        for linha in logs:
            mensagem_log.append('-- em %s foram %s registros não importados de %s analisados.' % (linha.data_hora.strftime("%d/%m/%Y as %H:%M:%S"), linha.nao_importados, linha.reg_analisados))

    for i in itens:
        # teoricamente pode vir mais de um empenho no mesmo arquivo
        for c in range(1, 21):
            if not i['GR-UG-GESTAO-AN-NUMERO-NEUQ(%s)' % c]:
                continue

            numero = i['GR-UG-GESTAO-AN-NUMERO-NEUQ(%s)' % c][11:]
            emitente_ug = get_or_create_unidade_gestora(i['GR-UG-GESTAO-AN-NUMERO-NEUQ(%s)' % c][:6])

            try:
                nota_empenho = NotaEmpenho.objects.get(emitente_ug=emitente_ug, numero=numero)
            except NotaEmpenho.DoesNotExist:
                nota_empenho = NotaEmpenho(emitente_ug=emitente_ug, numero=numero)

            nota_empenho.data_emissao = i['IT-DA-EMISSAO']
            nota_empenho.favorecido_original = i['IT-CO-FAVORECIDO']

            if len(i['IT-CO-FAVORECIDO']) == 11:
                qs = Vinculo.objects.filter(pessoa__pessoafisica__cpf=mask_cpf(i['IT-CO-FAVORECIDO'])).order_by('-tipo_relacionamento__model')
                if qs.exists():
                    vinculo_favorecido = qs[0]
                else:
                    vinculo_favorecido = PessoaExterna.objects.create(cpf=mask_cpf(i['IT-CO-FAVORECIDO'])).get_vinculo()

                nota_empenho.vinculo_favorecido = vinculo_favorecido

            elif len(i['IT-CO-FAVORECIDO']) == 14:
                pj, created = PessoaJuridica.objects.get_or_create(cnpj=mask_cnpj(i['IT-CO-FAVORECIDO']))
                nota_empenho.vinculo_favorecido = pj.get_vinculo()

            nota_empenho.observacao = i['IT-TX-OBSERVACAO']
            nota_empenho.evento = get_or_create_evento(i['GR-CODIGO-EVENTO'])
            nota_empenho.esfera_orcamentaria = get_or_create_esfera_orcamentaria(i['IT-IN-ESFERA-ORCAMENTARIA']) if i['IT-IN-ESFERA-ORCAMENTARIA'] else None
            nota_empenho.ptres = get_or_create_ptres(i['IT-CO-PROGRAMA-TRABALHO-RESUMIDO']) if i['IT-CO-PROGRAMA-TRABALHO-RESUMIDO'] else None
            nota_empenho.fonte_recurso = get_or_create_fonte_recurso(i['GR-FONTE-RECURSO'][1:4]) if i['GR-FONTE-RECURSO'] else None
            nota_empenho.fonte_recurso_original = i['GR-FONTE-RECURSO'] or ''
            nota_empenho.natureza_despesa = get_or_create_natureza_despesa(i['GR-NATUREZA-DESPESA']) if i['GR-NATUREZA-DESPESA'] else None
            nota_empenho.ugr = get_or_create_unidade_gestora(i['IT-CO-UG-RESPONSAVEL']) if i['IT-CO-UG-RESPONSAVEL'] else None
            nota_empenho.plano_interno = get_or_create_plano_interno(i['IT-CO-PLANO-INTERNO']) if i['IT-CO-PLANO-INTERNO'] else None
            nota_empenho.tipo = i['IT-IN-EMPENHO'] or ''
            nota_empenho.modalidade_licitacao = get_or_create_modalidade_licitacao(i['IT-IN-MODALIDADE-LICITACAO']) if i['IT-IN-MODALIDADE-LICITACAO'] else None
            nota_empenho.amparo_legal = i['IT-TX-AMPARO-LEGAL'] or ''
            nota_empenho.inciso = i['IT-CO-INCISO'] or ''
            nota_empenho.processo = i['IT-NU-PROCESSO'] or ''
            nota_empenho.origem_material = i['IT-IN-ORIGEM-MATERIAL'] or ''

            referencia = get_or_none_nota_empenho(emitente_ug.codigo, i['GR-AN-NU-DOCUMENTO-REFERENCIA'])

            nota_empenho.referencia_empenho = referencia
            nota_empenho.referencia_empenho_original = i['GR-AN-NU-DOCUMENTO-REFERENCIA'] or ''
            nota_empenho.referencia_ug = get_or_create_unidade_gestora(i['IT-CO-UG-DOC-REFERENCIA']) if i['IT-CO-UG-DOC-REFERENCIA'] else None
            nota_empenho.referencia_dispensa = i['IT-TX-REFERENCIA-DISPENSA'] or ''
            nota_empenho.valor = formata_decimal(i['IT-VA-TRANSACAO'])

            qs = Vinculo.objects.filter(pessoa__pessoafisica__cpf=mask_cpf(i['IT-CO-USUARIO'])).order_by('-tipo_relacionamento__model')
            if qs.exists():
                vinculo_operador = qs[0]
            else:
                vinculo_operador = PessoaExterna.objects.create(cpf=mask_cpf(i['IT-CO-USUARIO'])).get_vinculo()
            nota_empenho.vinculo_operador = vinculo_operador
            nota_empenho.ug_operador, created = UnidadeGestora.objects.get_or_create(codigo=i['IT-CO-UG-OPERADOR'])

            nota_empenho.codigo_terminal = i['IT-CO-TERMINAL-USUARIO'] or ''
            nota_empenho.data_transacao = i['IT-DAHO-TRANSACAO']

            try:
                nota_empenho.save()

                if i['IT-NU-LISTA(%s)' % c]:
                    # tenta cadastrar a lista de itens informada para o empenho
                    try:
                        cod_instituto = apps.get_model('comum', 'configuracao').objects.get(chave='instituicao_identificador').valor
                        numero_lista = i['IT-NU-LISTA(%s)' % c]
                        numero_original = '%s%s%s' % (emitente_ug.codigo, cod_instituto, numero_lista)

                        lista, li_created = NEListaItens.objects.get_or_create(numero=numero_lista, numero_original=numero_original)

                        lista.nota_empenho = nota_empenho
                        lista.save()

                        if not li_created and False:
                            # atualiza o subitem de natureza de despesa dos elementos, que podem ter sido importados anteriormente
                            itens = NEItem.objects.filter(lista_itens=lista)
                            for it in itens:
                                if not it.subitem and lista.nota_empenho.get_natureza_despesa():
                                    sbe, sb_created = SubElementoNaturezaDespesa.objects.get_or_create(
                                        natureza_despesa=lista.nota_empenho.get_natureza_despesa(), codigo_subelemento=i['IT-NU-ND-SUBITEM']
                                    )
                                    it.subitem = sbe
                                    it.save()

                    except Exception as e:
                        nota_empenho.delete()
                        registros_naoimportados += 1
                        mensagem_log.append('-- %s não importado. erro: %s' % (numero, e))

            except Exception as e:
                registros_naoimportados += 1
                mensagem_log.append('-- %s não importado. erro: %s' % (numero, e))

    log = LogImportacaoSIAFI(
        tipo=3, data_hora=datetime.now(), nome_arquivo=arquivo, reg_analisados=registros, nao_importados=registros_naoimportados, detalhamento='\n'.join(mensagem_log)
    )
    log.save()


def importar_notas_empenho_2(nome_arquivo_ref, nome_arquivo_txt):
    """
    Esta função foi criada para tratar o novo arquivo REF nota_empenho_2.ref.
    Por enquanto faz a mesma coisa da função importar_notas_empenho, mas futuramente 
    os campos adicionais deverão ser tratados.
    """
    importar_notas_empenho(nome_arquivo_ref, nome_arquivo_txt)


def importar_itens_empenho(nome_arquivo_ref, nome_arquivo_txt):
    itens = get_itens(nome_arquivo_ref, nome_arquivo_txt)

    # número de registros
    registros = len(itens)
    registros_naoimportados = 0

    # logs
    mensagem_log = []
    arquivo = nome_arquivo_txt.split('/')[-1]

    logs = LogImportacaoSIAFI.objects.filter(nome_arquivo=arquivo)
    if logs:
        mensagem_log.append('-- o arquivo %s já foi importado anteriormente' % arquivo)
        for linha in logs:
            mensagem_log.append('-- em %s foram %s registros não importados de %s analisados.' % (linha.data_hora.strftime("%d/%m/%Y as %H:%M:%S"), linha.nao_importados, linha.reg_analisados))

    for i in itens:
        numero = i['GR-UG-GESTAO-AN-NUMERO-LI'][11:]
        num_item = i['IT-NU-ITEM']
        get_or_create_unidade_gestora(i['GR-UG-GESTAO-AN-NUMERO-LI'][:6])

        lista = get_or_none_lista_itens_empenho(i['GR-UG-GESTAO-AN-NUMERO-LI'])
        if not lista:
            lista = NEListaItens(numero=numero, numero_original=i['GR-UG-GESTAO-AN-NUMERO-LI'])
            lista.save()

        try:
            item = NEItem.objects.get(lista_itens=lista, numero=int(num_item))
        except Exception:
            item = NEItem(lista_itens=lista, numero=int(num_item))

        item.subitem_original = i['IT-NU-ND-SUBITEM']

        if lista.nota_empenho and lista.nota_empenho.get_natureza_despesa():
            subelemento, sb_created = SubElementoNaturezaDespesa.objects.get_or_create(
                natureza_despesa=lista.nota_empenho.get_natureza_despesa(), codigo_subelemento=i['IT-NU-ND-SUBITEM']
            )
            item.subitem = subelemento

        descricao = ''
        for c in range(1, 21):
            if i['IT-TX-DESCRICAO-ITEM(%s)' % c]:
                descricao += i['IT-TX-DESCRICAO-ITEM(%s)' % c]
        item.descricao = descricao

        # a quantidade de um item no arquivo do siafi é do tipo numeric(10,5)
        item.quantidade = formata_decimal_casas_decimais(i['IT-QT-UNIDADE-ITEM'], 5) if i['IT-QT-UNIDADE-ITEM'] else 0

        item.valor_unitario = formata_decimal(i['IT-VA-UNIDADE-ITEM']) if i['IT-VA-UNIDADE-ITEM'] else 0
        item.valor_total = formata_decimal(i['IT-VA-TOTAL-ITEM']) if i['IT-VA-TOTAL-ITEM'] else 0

        item.data_transacao = i['IT-DAHO-TRANSACAO']

        try:
            item.save()
        except Exception as e:
            registros_naoimportados += 1
            mensagem_log.append('-- item %s da lista %s não importado. erro: %s' % (num_item, i['GR-UG-GESTAO-AN-NUMERO-LI'], e))

    log = LogImportacaoSIAFI(
        tipo=4, data_hora=datetime.now(), nome_arquivo=arquivo, reg_analisados=registros, nao_importados=registros_naoimportados, detalhamento='\n'.join(mensagem_log)
    )
    log.save()


def importar_notas_sistema(nome_arquivo_ref, nome_arquivo_txt):
    """
    Nota: essa função trata 2 arquivos REF: nota_sistema.ref e nota_sistema_2.ref.
    """
    itens = get_itens(nome_arquivo_ref, nome_arquivo_txt)

    # número de registros
    registros = len(itens)
    registros_naoimportados = 0

    # logs
    mensagem_log = []
    arquivo = nome_arquivo_txt.split('/')[-1]

    logs = LogImportacaoSIAFI.objects.filter(nome_arquivo=arquivo)
    if logs:
        mensagem_log.append('-- o arquivo %s já foi importado anteriormente' % arquivo)
        for linha in logs:
            mensagem_log.append('-- em %s foram %s registros não importados de %s analisados.' % (linha.data_hora.strftime("%d/%m/%Y as %H:%M:%S"), linha.nao_importados, linha.reg_analisados))

    for i in itens:
        numero = i['GR-UG-GESTAO-AN-NUMERO-NSUQ'][11:]
        emissao = i['IT-DA-EMISSAO']
        transacao = i['IT-DAHO-TRANSACAO']
        valorizacao = i['IT-DA-VALORIZACAO']
        ug = i['GR-UG-GESTAO-AN-NUMERO-NSUQ'][0:6]
        gestao = i['GR-UG-GESTAO-AN-NUMERO-NSUQ'][6:11]
        titulo_credito = i['IT-CO-TITULO-CREDITO'] if i['IT-CO-TITULO-CREDITO'] else None
        ven_tit_credito = i['IT-DA-VENCIMENTO-TITULO-CREDITO']
        obs = i['IT-TX-OBSERVACAO']
        origem = i['IT-CO-SISTEMA-ORIGEM'] or None

        # indica se o registro já existe no sistema ou se está sendo criado agora
        created = False

        # verifica se já existe a nota de credito caso contrário cadastra
        try:
            nota_sistema = NotaSistema.objects.get(numero=numero, ug__codigo=ug)
        except NotaSistema.DoesNotExist:
            nota_sistema = NotaSistema(numero=numero)
            created = True

        nota_sistema.data_emissao = emissao
        nota_sistema.data_valorizacao = valorizacao
        nota_sistema.datahora_transacao = transacao
        nota_sistema.gestao = get_or_create_classificacao_institucional(gestao)
        nota_sistema.ug = get_or_create_unidade_gestora(ug)
        nota_sistema.titulo_credito = titulo_credito
        nota_sistema.data_venc_tit_credito = ven_tit_credito
        nota_sistema.observacao = obs
        nota_sistema.sistema_origem = origem

        try:
            nota_sistema.save()
        except Exception as e:
            registros_naoimportados += 1
            mensagem_log.append('-- %s não importado. erro: %s' % (numero, e))
            continue

        # Tratamento dos itens da nota de crédito; essa é a parte que é flexível ao
        # ponto de tratar os dois tipos de layout: nota_sistema.ref e nota_sistema_2.ref.
        if created:
            for c in range(1, 101):
                if i.get('GR-CODIGO-EVENTO(%s)' % c):
                    c_evento = i['GR-CODIGO-EVENTO(%s)' % c]
                    inscricao_1 = i['IT-CO-INSCRICAO1(%s)' % c] or None
                    inscricao_2 = i['IT-CO-INSCRICAO2(%s)' % c] or None
                    classific_1 = i['GR-CLASSIFICACAO1(%s)' % c]
                    classific_2 = i['GR-CLASSIFICACAO2(%s)' % c]
                    valor = formata_decimal(i['IT-VA-TRANSACAO(%s)' % c])

                    evento = get_or_create_evento(c_evento)
                    itemNS = NotaSistemaItem(nota_sistema=nota_sistema, evento=evento, inscricao_1=inscricao_1, inscricao_2=inscricao_2, valor=valor)

                    # criando elementos para o campo classific_1
                    if classific_1:
                        classif_despesa_1 = get_or_create_classificacao_despesa(classific_1[0:1])
                        natureza_despesa_1 = get_or_create_natureza_despesa(classific_1[1:7])
                        subitem_1, sb_ctd = SubElementoNaturezaDespesa.objects.get_or_create(natureza_despesa=natureza_despesa_1, codigo_subelemento=classific_1[7:9])

                        itemNS.classif_desp_1 = classif_despesa_1
                        itemNS.despesa_1 = subitem_1

                    # criando elementos para o campo classific_2
                    if classific_2:
                        classif_despesa_2 = get_or_create_classificacao_despesa(classific_2[0:1])
                        natureza_despesa_2 = get_or_create_natureza_despesa(classific_2[1:7])
                        subitem_2, sb_ctd = SubElementoNaturezaDespesa.objects.get_or_create(natureza_despesa=natureza_despesa_2, codigo_subelemento=classific_2[7:9])

                        itemNS.classif_desp_2 = classif_despesa_2
                        itemNS.despesa_2 = subitem_2

                    itemNS.save()

    log = LogImportacaoSIAFI(
        tipo=2, data_hora=datetime.now(), nome_arquivo=arquivo, reg_analisados=registros, nao_importados=registros_naoimportados, detalhamento='\n'.join(mensagem_log)
    )
    log.save()


def importar_ordens_bancarias(nome_arquivo_ref, nome_arquivo_txt):
    itens = get_itens(nome_arquivo_ref, nome_arquivo_txt)
    for i in itens:
        import pprint

        pprint.pprint(i)
        break


# métodos de apoio, apenas utilizados para analisar algumas informações - serão removidos posteriormente
def verificar_varias_listas_empenho():
    itens = get_itens('/Users/anderson/Desktop/siafi/EMPENHOS_NE_20110929.ref', '/Users/anderson/Desktop/siafi/EMPENHOS_NE_20110929.txt')
    for i in itens:
        nListas = 0
        for c in range(1, 21):
            if i['IT-NU-LISTA(%s)' % c]:
                nListas += 1
        print(('EMPENHO: %s - LISTAS: %s' % (i['GR-UG-GESTAO-AN-NUMERO-NEUQ(1)'], nListas)))


def verificar_varios_empenhos():
    itens = get_itens('/Users/anderson/Desktop/siafi/EMPENHOS_NE_20110929.ref', '/Users/anderson/Desktop/siafi/EMPENHOS_NE_20110929.txt')
    for i in itens:
        nEmpenhos = 0
        for c in range(1, 21):
            if i['GR-UG-GESTAO-AN-NUMERO-NEUQ(%s)' % c]:
                nEmpenhos += 1
        if nEmpenhos > 1:
            print(('EMPENHO 1: %s - QTD: %s' % (i['GR-UG-GESTAO-AN-NUMERO-NEUQ(1)'], nEmpenhos)))


def verificar_eventos_empenhos():
    itens = get_itens('/Users/anderson/Desktop/siafi/EMPENHOS_NE_20110929.ref', '/Users/anderson/Desktop/siafi/EMPENHOS_NE_20110929.txt')
    eventos = []
    empenhos = []
    for i in itens:
        if not i['GR-CODIGO-EVENTO'] in eventos:
            eventos.append(i['GR-CODIGO-EVENTO'])

        if (i['GR-CODIGO-EVENTO'] == '406093') or (i['GR-CODIGO-EVENTO'] == '406095'):
            empenhos.append([i['GR-UG-GESTAO-AN-NUMERO-NEUQ(1)'], i['GR-CODIGO-EVENTO'], i['IT-CO-FAVORECIDO']])
    print(empenhos)


def processar():
    """Função principal que lê o conteúdo da pasta financeiro/arquivos e os processa"""
    ordem = [
        'municipio',
        'credor',
        'unidade_gestora',
        'evento',
        'ptres',
        'programa_trabalho',
        'plano_interno',
        'nota_credito',
        'nota_credito_2',
        'nota_dotacao',
        'nota_empenho',
        'nota_empenho_2',
        'nota_empenho_3',
        'item_empenho',
        'nota_sistema',
        'nota_sistema_2',
        'nota_sistema_3',
        'nota_sistema_4',
        'nota_sistema_5',
    ]

    descompactar_arquivos(FINANCEIRO_ARQUIVOS)
    arquivos_identificados = dict()  # chave: 'layout', valor: ['txt1', 'txt2']

    for ref_filename in [i for i in os.listdir(FINANCEIRO_ARQUIVOS) if i.endswith('.REF')]:
        txt_filename = ref_filename.replace('.REF', '.TXT')
        ref_filepath = os.path.join(FINANCEIRO_ARQUIVOS, ref_filename)
        txt_filepath = os.path.join(FINANCEIRO_ARQUIVOS, txt_filename)

        # Até onde sabemos entra aqui se o arquivo gzip do TXT veio corrompido.
        if not os.path.exists(txt_filepath):
            os.remove(ref_filepath)
            continue

        # Identificando o layout.
        tipo_layout = identificar_layout(ref_filepath)
        if tipo_layout is None:
            print((colorize('Arquivo com layout desconhecido: %s' % ref_filename, fg='black', bg='yellow')))
            continue

        # Adicionando o par na lista de ``arquivos_identificados``
        if tipo_layout not in arquivos_identificados:
            arquivos_identificados[tipo_layout] = []
        arquivos_identificados[tipo_layout].append([ref_filepath, txt_filepath])

    for layout in ordem:
        if arquivos_identificados.get(layout):
            for item in arquivos_identificados.get(layout):
                ref_filepath, txt_filepath = item
                x0 = datetime.now()
                processar_arquivo(layout, ref_filepath, txt_filepath)
                tempo = datetime.now() - x0
                print((colorize('Processado %s\t\t%s' % (txt_filepath.split('/')[-1], tempo), fg='green')))


def processar_arquivo(layout, ref_filepath, txt_filepath):
    """Efetivamente invoca a função de processamento do ``layout``"""
    layouts = dict(
        municipio=importar_municipios,
        credor=importar_credores,
        unidade_gestora=importar_unidades_gestoras,
        evento=importar_eventos,
        programa_trabalho=importar_programas_trabalho,
        ptres=importar_ptres,
        plano_interno=importar_planos_internos,
        nota_credito=importar_notas_credito,
        nota_credito_2=importar_notas_credito_2,
        nota_dotacao=importar_notas_dotacao,
        nota_empenho=importar_notas_empenho,
        nota_empenho_2=importar_notas_empenho_2,
        nota_empenho_3=importar_notas_empenho_2,
        item_empenho=importar_itens_empenho,
        nota_sistema=importar_notas_sistema,
        nota_sistema_2=importar_notas_sistema,
        nota_sistema_3=importar_notas_sistema,
        nota_sistema_4=importar_notas_sistema,
        nota_sistema_5=importar_notas_sistema,
        ordem_bancaria=importar_ordens_bancarias,
    )

    try:
        funcao = layouts[layout]
    except KeyError:
        print(('Layout %s sem funcao de processamento' % layout))
        return

    ref_filename, txt_filename = os.path.split(ref_filepath)[-1], os.path.split(txt_filepath)[-1]
    print((colorize('>>> Processando: %s, %s, %s' % (layout, ref_filename, txt_filename), fg='yellow')))
    funcao(ref_filepath, txt_filepath)
    os.rename(ref_filepath, os.path.join(FINANCEIRO_ARQUIVOS_PROCESSADOS, ref_filename))
    os.rename(txt_filepath, os.path.join(FINANCEIRO_ARQUIVOS_PROCESSADOS, txt_filename))
