from almoxarifado.models import CategoriaMaterialConsumo, MaterialConsumo, Empenho, MaterialTipo
from processo_eletronico.models import TipoProcesso


def initial_data():
    categoria_material_consumo, _ = CategoriaMaterialConsumo.get_or_create(codigo="0", nome="Categoria Material Consumo")

    material_consumo, _ = MaterialConsumo.get_or_create(categoria=categoria_material_consumo, nome="Material de Consumo")

    material_tipo, _ = MaterialTipo.get_or_create(nome='consumo')

    empenho, _ = Empenho.get_or_create(numero='20193012RE', tipo_material=material_tipo)

    tipo_processo, _ = TipoProcesso.get_or_create(nome='Tipo de Processo')
