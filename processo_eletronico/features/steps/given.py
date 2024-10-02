# -*- coding: utf-8 -*-
from behave import given
from django.apps.registry import apps
import datetime
from comum.models import Municipio
from djtools.new_tests.test_initial_data import cadastrar_setor, definir_endereco
from rh.models import Atividade
from documento_eletronico.models import DocumentoTexto, ModeloDocumento, Documento, TipoDocumentoTextoHistoricoConteudo, TipoDocumento
from django.core.management import call_command

TipoProcesso = apps.get_model('processo_eletronico', 'TipoProcesso')
Servidor = apps.get_model('rh', 'Servidor')
Funcao = apps.get_model('rh', 'Funcao')
ServidorFuncaoHistorico = apps.get_model('rh', 'ServidorFuncaoHistorico')
Setor = apps.get_model('rh', 'Setor')


@given('os dados básicos para o processo eletronico')
def step_dados_basicos_processo(context):
    # tipoprocesso = TipoProcesso.objects.get(nome='Pessoal: Adicional de Insalubridade')
    municipio, _ = Municipio.objects.get_or_create(nome='Natal', uf='RN', codigo='NAT')
    endereco = {'endereco': 'Rua Dr. Nilo Bezerra Ramalho, 1692, Tirol', 'cep      ': '59015-300', 'municipio': municipio}

    setor_raiz_suap, setor_raiz_siape = cadastrar_setor('RAIZ', None, 'RAIZ')

    setor_re_suap, setor_re_siape = cadastrar_setor('RE', setor_raiz_siape, 'RE')
    definir_endereco(setor_re_suap.uo, endereco)
    definir_endereco(setor_re_siape.uo, endereco)
    funcao = Funcao.objects.get(nome="Reitor", codigo=Funcao.CODIGO_CD)
    atividade = Atividade.objects.get(codigo=Atividade.REITOR, nome='Reitor')
    servidor_b = Servidor.objects.get(matricula='ServidorB')
    ServidorFuncaoHistorico.objects.get_or_create(
        servidor=servidor_b, data_inicio_funcao=datetime.date(2010, 1, 1), atividade=atividade, funcao=funcao, setor=setor_re_siape, setor_suap=setor_re_suap
    )


@given('os usuários do processo eletronico')
def step_usuarios_processo(context):
    setor_suap = Setor.suap.get(sigla='A1')
    setor_siape = Setor.siape.get(sigla='A1')
    servidor = Servidor.objects.get(matricula='128002')
    funcao = Funcao.objects.get(codigo=Funcao.CODIGO_FG)
    ServidorFuncaoHistorico.objects.get_or_create(servidor=servidor, data_inicio_funcao=datetime.date(2010, 1, 1), funcao=funcao, setor=setor_siape, setor_suap=setor_suap)
    # Define papel do operador de processo 1
    servidor1 = Servidor.objects.get(matricula='128001')
    servidor1._definir_papel_do_servidor()

    setor_suap = Setor.suap.get(sigla='A2')
    setor_siape = Setor.siape.get(sigla='A2')
    servidor = Servidor.objects.get(matricula='128004')
    funcao = Funcao.objects.get(codigo=Funcao.CODIGO_FG)
    ServidorFuncaoHistorico.objects.get_or_create(servidor=servidor, data_inicio_funcao=datetime.date(2010, 1, 1), funcao=funcao, setor=setor_siape, setor_suap=setor_suap)


@given('os cadastros de documentos eletronicos')
def step_cadastros_documento_eletronico_basicos(context):
    # chama command fixtures com dados dados basicos
    call_command('loaddata', 'documento_eletronico/fixtures/initial_data_01_classificacao.json')
    call_command('loaddata', 'documento_eletronico/fixtures/initial_data_02_tipo_documento.json')
    call_command('loaddata', 'documento_eletronico/fixtures/initial_data_03_modelo_documento.json')
    call_command('loaddata', 'documento_eletronico/fixtures/initial_data_04_tipo_conferencia.json')
    call_command('loaddata', 'documento_eletronico/fixtures/initial_data_05_tipo_vinculo_documento.json')
    call_command('loaddata', 'documento_eletronico/fixtures/initial_data_06_hipotese_legal.json')

    setor_suap = Setor.suap.get(sigla='A2')
    # Operador de processo 2
    servidor = Servidor.objects.get(matricula='128003')

    user = servidor.user
    modelo = ModeloDocumento.objects.last()

    # Adiciona Tipo
    tipo_termo = TipoDocumento()
    tipo_termo.nome = "Termo"
    tipo_termo.sigla = "Termo"
    tipo_termo.ativo = True
    tipo_termo.save()

    # Adiciona documento interno
    TipoDocumentoTextoHistoricoConteudo.objects.create(
        tipo_documento_texto=modelo.tipo_documento_texto, area_conteudo=TipoDocumentoTextoHistoricoConteudo.CABECALHO,
        conteudo=modelo.tipo_documento_texto.cabecalho_padrao, hash=modelo.tipo_documento_texto.cabecalho_hash
    )
    TipoDocumentoTextoHistoricoConteudo.objects.create(
        tipo_documento_texto=modelo.tipo_documento_texto, area_conteudo=TipoDocumentoTextoHistoricoConteudo.RODAPE,
        conteudo=modelo.tipo_documento_texto.rodape_padrao, hash=modelo.tipo_documento_texto.rodape_hash
    )

    documento_texto = DocumentoTexto()
    documento_texto.setor_dono = setor_suap
    documento_texto.usuario_criacao = user
    documento_texto.assunto = "Documento Teste"
    documento_texto.data_ultima_modificacao = datetime.datetime.now()
    documento_texto.usuario_ultima_modificacao = user
    documento_texto.modelo = modelo
    documento_texto.nivel_acesso = Documento.NIVEL_ACESSO_PUBLICO

    documento_texto.save()

    servidor._definir_papel_do_servidor()

    documento_texto.concluir()
    documento_texto.atribuir_identificador_e_processar_conteudo_final(
        identificador_tipo_documento_sigla="OFICIO",
        identificador_numero=1,
        identificador_ano=2020,
        identificador_setor_sigla="A2",
        data_emissao=datetime.datetime.now(),
        identificador_dono_documento=None
    )
    documento_texto.save()

    documento_texto.assinar_via_senha(user, servidor.papeis_ativos[0], documento_texto.data_criacao)
    print("{}".format(servidor.papeis_ativos[0]))
    documento_texto.finalizar_documento()
    documento_texto.save()

    if documento_texto.estah_finalizado:
        print("Documento {} do setor {} está finalizado".format(documento_texto.id, documento_texto.setor_dono.sigla))
    else:
        print("Documento {} do setor {} NÃO está finalizado".format(documento_texto.id, documento_texto.setor_dono.sigla))

    # Todo: Verificar como podemos adicionar o teste de upload no behave

    #
    # #Adiciona documento externo (upload)
    #
    #
    #
    # documento_digitalizado= DocumentoDigitalizado.criar(file_content="DOCUMENTO DIGITALIZADO TESTE BEHAVE",
    #                                                                   file_name='TESTE.PDF',
    #                                                                   tipo_documento=TipoDocumento.objects.first(),
    #                                                                   assunto="Teste behave processos eletrôncicos",
    #                                                                   user=user,
    #                                                                   papel= servidor.papeis_ativos[0],
    #                                                                   nivel_acesso=DocumentoDigitalizado.NIVEL_ACESSO_PUBLICO)
    #
