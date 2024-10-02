# -*- coding: utf-8 -*-

from behave import given
import datetime
from decimal import Decimal
from django.apps.registry import apps

VeiculoMarca = apps.get_model('estacionamento', 'VeiculoMarca')
VeiculoTipo = apps.get_model('estacionamento', 'VeiculoTipo')
VeiculoEspecie = apps.get_model('estacionamento', 'VeiculoEspecie')
VeiculoTipoEspecie = apps.get_model('estacionamento', 'VeiculoTipoEspecie')
VeiculoModelo = apps.get_model('estacionamento', 'VeiculoModelo')
Municipio = apps.get_model('comum', 'Municipio')
VeiculoCor = apps.get_model('estacionamento', 'VeiculoCor')
ViaturaGrupo = apps.get_model('frota', 'ViaturaGrupo')
InventarioStatus = apps.get_model('patrimonio', 'InventarioStatus')
Setor = apps.get_model('rh', 'Setor')
UnidadeOrganizacional = apps.get_model('rh', 'UnidadeOrganizacional')
Entrada = apps.get_model('almoxarifado', 'Entrada')
EntradaTipo = apps.get_model('almoxarifado', 'EntradaTipo')
MaterialTipo = apps.get_model('almoxarifado', 'MaterialTipo')
CategoriaMaterialPermanente = apps.get_model('patrimonio', 'CategoriaMaterialPermanente')
EntradaPermanente = apps.get_model('patrimonio', 'EntradaPermanente')
Inventario = apps.get_model('patrimonio', 'Inventario')
ViaturaStatus = apps.get_model('frota', 'ViaturaStatus')
VeiculoCombustivel = apps.get_model('estacionamento', 'VeiculoCombustivel')
Viatura = apps.get_model('frota', 'Viatura')
Servidor = apps.get_model('rh', 'Servidor')
MotoristaTemporario = apps.get_model('frota', 'MotoristaTemporario')
PessoaFisica = apps.get_model('rh', 'PessoaFisica')


@given('os dados básicos para frota')
def step_dados_basicos_frota(context):
    veiculomarca = VeiculoMarca.objects.get_or_create(nome='Ford')[0]
    veiculotipo = VeiculoTipo.objects.get_or_create(descricao='Utilitário')[0]
    veiculoespecie = VeiculoEspecie.objects.get_or_create(descricao='Comum')[0]
    veiculotipoespecie = VeiculoTipoEspecie.objects.get_or_create(tipo=veiculotipo, especie=veiculoespecie)[0]
    VeiculoModelo.objects.get_or_create(nome='Ranger', marca=veiculomarca, tipo_especie=veiculotipoespecie)[0]
    VeiculoCor.objects.get_or_create(nome='Branca')[0]
    Municipio.get_or_create(nome='Natal', uf='RN')[0]
    ViaturaGrupo.objects.get_or_create(codigo='123', nome='Carro de Passeio', descricao='Carro para transporte de passageiro')[0]
    inventariostatus = InventarioStatus.objects.get_or_create(nome='Status')[0]
    setor = Setor.objects.get(sigla='CZN')
    unidadeorganizacional = UnidadeOrganizacional.objects.suap().get(setor=setor)
    entrada = Entrada.objects.get_or_create(data=datetime.datetime.now(), uo=unidadeorganizacional, tipo_entrada=EntradaTipo.DOACAO(), tipo_material=MaterialTipo.PERMANENTE())[0]
    categoriamaterialpermanente = CategoriaMaterialPermanente.objects.get_or_create(codigo='0', nome='nome')[0]
    entradapermanente = EntradaPermanente.objects.get_or_create(entrada=entrada, categoria=categoriamaterialpermanente, descricao='descrição', qtd=1, valor=Decimal(10))[0]
    Inventario.objects.get_or_create(numero=123456, status=inventariostatus, entrada_permanente=entradapermanente, campo_busca='0')[0]
    ViaturaStatus.objects.get_or_create(descricao='Ativa')[0]
    VeiculoCombustivel.objects.get_or_create(nome='Gasolina')[0]
