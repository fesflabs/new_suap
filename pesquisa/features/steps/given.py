from decimal import Decimal

from django.contrib.auth.models import Group
from behave import given
from datetime import datetime

from almoxarifado.models import Entrada, EntradaTipo, MaterialTipo
from comum.models import Ano
from financeiro.models import CategoriaEconomicaDespesa, ElementoDespesa, GrupoNaturezaDespesa, ModalidadeAplicacao, NaturezaDespesa
from django.apps.registry import apps
from cnpq.models import GrupoPesquisa, CurriculoVittaeLattes, DadoComplementar, DadoGeral
from patrimonio.models import InventarioStatus, CategoriaMaterialPermanente, EntradaPermanente, Inventario
from pesquisa.models import RegistroConclusaoProjeto
from rh.models import Setor

CategoriaBolsa = apps.get_model('ae', 'categoriabolsa')
PessoaFisica = apps.get_model('rh', 'PessoaFisica')
UnidadeOrganizacional = apps.get_model('rh', 'UnidadeOrganizacional')
Aluno = apps.get_model('edu', 'Aluno')
SituacaoMatricula = apps.get_model('edu', 'SituacaoMatricula')
Servidor = apps.get_model('rh', 'Servidor')
Projeto = apps.get_model('pesquisa', 'Projeto')
AvaliadorIndicado = apps.get_model('pesquisa', 'AvaliadorIndicado')
AreaConhecimento = apps.get_model('rh', 'AreaConhecimento')
OrigemRecursoEdital = apps.get_model('pesquisa', 'OrigemRecursoEdital')
Titulacao = apps.get_model('rh', 'Titulacao')
LinhaEditorial = apps.get_model('pesquisa', 'LinhaEditorial')
PrestadorServico = apps.get_model('comum', 'PrestadorServico')


@given('os dados básicos para a pesquisa')
def step_dados_basicos_pesquisa(context):
    areaconhecimento = AreaConhecimento.objects.get_or_create(codigo='10000003', descricao='CIÊNCIAS EXATAS E DA TERRA')[0]
    AreaConhecimento.objects.get_or_create(codigo='10100008', descricao='MATEMÁTICA', superior=areaconhecimento)
    AreaConhecimento.objects.get_or_create(codigo='10100009', descricao='BIOQUÍMICA', superior=areaconhecimento)
    categoriaeconomicadespesa = CategoriaEconomicaDespesa.objects.get_or_create(codigo='3', nome='Despesas Correntes')[0]
    gruponaturezadespesa = GrupoNaturezaDespesa.objects.get_or_create(codigo='3', nome='Outras Despesas Correntes')[0]
    modalidadeaplicacao = ModalidadeAplicacao.objects.get_or_create(codigo='90', nome='Aplicações Diretas')[0]
    elementodespesa1 = ElementoDespesa.objects.get_or_create(codigo='30', nome='Material de Consumo')[0]
    elementodespesa2 = ElementoDespesa.objects.get_or_create(codigo='18', nome='Auxílio Financeiro a Estudantes')[0]
    elementodespesa3 = ElementoDespesa.objects.get_or_create(codigo='20', nome='Auxílio Financeiro a Pesquisadores')[0]

    NaturezaDespesa.objects.get_or_create(
        categoria_economica_despesa=categoriaeconomicadespesa,
        grupo_natureza_despesa=gruponaturezadespesa,
        modalidade_aplicacao=modalidadeaplicacao,
        elemento_despesa=elementodespesa1,
        codigo='339030',
        nome=elementodespesa1.nome,
    )

    NaturezaDespesa.objects.get_or_create(
        categoria_economica_despesa=categoriaeconomicadespesa,
        grupo_natureza_despesa=gruponaturezadespesa,
        modalidade_aplicacao=modalidadeaplicacao,
        elemento_despesa=elementodespesa2,
        codigo='339018',
        nome=elementodespesa2.nome,
    )

    NaturezaDespesa.objects.get_or_create(
        categoria_economica_despesa=categoriaeconomicadespesa,
        grupo_natureza_despesa=gruponaturezadespesa,
        modalidade_aplicacao=modalidadeaplicacao,
        elemento_despesa=elementodespesa3,
        codigo='339020',
        nome=elementodespesa3.nome,
    )
    OrigemRecursoEdital.objects.get_or_create(descricao='PROPI')

    if CategoriaBolsa:
        CategoriaBolsa.objects.get_or_create(nome='Bolsa de iniciação científica', descricao='Bolsa de iniciação científica', tipo_bolsa='iniciação científica')

    Titulacao.objects.create(nome='Doutorado', codigo='26', titulo_masculino='Dr.', titulo_feminino='Dra.')
    inventariostatus = InventarioStatus.objects.get_or_create(nome='Status')[0]
    setor = Setor.objects.get(sigla='CZN')
    unidadeorganizacional = UnidadeOrganizacional.objects.suap().get(setor=setor)
    entrada = Entrada.objects.get_or_create(data=datetime.now(), uo=unidadeorganizacional,
                                            tipo_entrada=EntradaTipo.DOACAO(), tipo_material=MaterialTipo.PERMANENTE())[
        0]
    categoriamaterialpermanente = CategoriaMaterialPermanente.objects.get_or_create(codigo='0', nome='nome')[0]
    entradapermanente = EntradaPermanente.objects.get_or_create(entrada=entrada, categoria=categoriamaterialpermanente,
                                                                descricao='equipamento do laboratório', qtd=1, valor=Decimal(10))[0]
    Inventario.objects.get_or_create(numero=123455, status=inventariostatus, entrada_permanente=entradapermanente,
                                     campo_busca='0')[0]


@given('os usuários da pesquisa')
def step_usuarios_pesquisa(context):
    grupo = GrupoPesquisa.objects.get_or_create(codigo='01', descricao='Grupo de Pesquisa', instituicao='IFRN')[0]

    curriculo = CurriculoVittaeLattes.objects.create(sistema_origem_xml='', numero_identificador='01')
    dado_complementar = DadoComplementar.objects.create()
    curriculo.dado_complementar = dado_complementar
    dado_geral = DadoGeral.objects.create(
        nome_completo='Coord_Proj',
        nome_citacao='Coord_Proj',
        nacionalidade='Brasileiro',
        cpf='921.728.444-03',
        numero_passaporte='921.728.444-03',
        pais_nascimento='Brasil',
        uf_nascimento='RN',
        cidade_nascimento='Natal',
        sexo='F',
        numero_identidade='111',
        orgao_emissor='ITEP',
        uf_orgao_emissor='RN',
        nome_pai='Nome do pai',
        nome_mae='Nome da mãe',
        permissao_divulgacao='Sim',
        nome_arquivo_foto='path',
        texto_resumo='Texto resumo',
        outras_informacoes_relevantes='outras informações relevantes',
    )
    coord_projeto = Servidor.objects.get(matricula='108003')
    curriculo.dado_geral = dado_geral
    curriculo.vinculo = coord_projeto.get_vinculo()
    curriculo.grupos_pesquisa.add(grupo)
    curriculo.save()

    coord_projeto.areas_de_conhecimento.add(AreaConhecimento.objects.all()[0])

    curriculo = CurriculoVittaeLattes.objects.create(sistema_origem_xml='', numero_identificador='02')
    dado_complementar = DadoComplementar.objects.create()
    curriculo.dado_complementar = dado_complementar
    dado_geral = DadoGeral.objects.create(
        nome_completo='Servidor_Proj',
        nome_citacao='Servidor_Proj',
        nacionalidade='Brasileiro',
        cpf='232.607.644-37',
        numero_passaporte='232.607.644-37',
        pais_nascimento='Brasil',
        uf_nascimento='RN',
        cidade_nascimento='Natal',
        sexo='F',
        numero_identidade='111',
        orgao_emissor='ITEP',
        uf_orgao_emissor='RN',
        nome_pai='Nome do pai',
        nome_mae='Nome da mãe',
        permissao_divulgacao='Sim',
        nome_arquivo_foto='path',
        texto_resumo='Texto resumo',
        outras_informacoes_relevantes='outras informações relevantes',
    )
    servidor_projeto = Servidor.objects.get(matricula='108004')
    curriculo.dado_geral = dado_geral
    curriculo.vinculo = servidor_projeto.get_vinculo()
    curriculo.grupos_pesquisa.add(grupo)
    curriculo.save()
    avaliador_projeto = Servidor.objects.get(matricula='108005')
    avaliador_projeto.areas_de_conhecimento.add(AreaConhecimento.objects.all()[0])
    avaliador_projeto.titulacao = Titulacao.objects.all()[0]
    avaliador_projeto.save()

    avaliador_projeto = Servidor.objects.get(matricula='108006')
    avaliador_projeto.areas_de_conhecimento.add(AreaConhecimento.objects.all()[0])
    avaliador_projeto.titulacao = Titulacao.objects.all()[0]
    avaliador_projeto.save()
    pessoafisica = PessoaFisica.objects.get(cpf='359.221.769-00')
    pessoafisica.lattes = 'http://buscatextual.cnpq.br/buscatextual/visualizacv.do?id=K4758430D7'
    pessoafisica.save()
    ano, created = Ano.objects.get_or_create(ano=str(datetime.now().year))
    situacao = SituacaoMatricula.objects.get_or_create(descricao='Matriculado', ativo=True)[0]

    aluno = Aluno.objects.get(matricula='20191101011081')
    aluno.ano_letivo = ano
    aluno.periodo_letivo = 1
    aluno.situacao = situacao
    aluno.ano_let_prev_conclusao = datetime.now().year
    aluno.save()


@given('os dados básicos para a editora')
def step_dados_basicos_editora(context):
    areaconhecimento = AreaConhecimento.objects.get_or_create(codigo='10000003', descricao='CIÊNCIAS EXATAS E DA TERRA')[0]
    AreaConhecimento.objects.get_or_create(codigo='10100008', descricao='MATEMÁTICA', superior=areaconhecimento)
    LinhaEditorial.objects.get_or_create(nome='Linha Editorial 01')
    LinhaEditorial.objects.get_or_create(nome='Linha Editorial 02')
    parecerista = PrestadorServico.objects.get(cpf='342.456.058-80')
    grupo = Group.objects.get(name='Parecerista de Obra')
    parecerista.pessoafisica.user.groups.add(grupo)


@given('os ajustes para o laboratório')
def step_dados_basicos_laboratorio(context):
    RegistroConclusaoProjeto.objects.update(dt_avaliacao=None)
