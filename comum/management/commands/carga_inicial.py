# -*- coding: utf-8 -*-

from django.apps import apps

from djtools.management.commands import BaseCommandPlus


# Tabelas para carda inicial --------------------------------------------------
# Para acrescentar outras cargas deve-se seguir o seguinte roteiro:
#    1 - Criar um vetor que conterá os itens a serem inseridos.
#        Cada linha deve conter um dicionário onde a chave deve ser os campos
#    2 - Criar uma nova linha no vetor carga_inicial_classes

licitacao_tipo_itens = [{'nome': 'dispensa'}, {'nome': 'pregao'}]
material_tipo_itens = [{'nome': 'consumo'}, {'nome': 'permanente'}]
entrada_tipo_itens = [{'nome': 'compra'}, {'nome': 'doacao'}]
baixa_tipo_itens = [{'nome': 'cessao'}, {'nome': 'doacao'}, {'nome': 'inservivel'}]
inventario_status_itens = [{'nome': 'pendente'}, {'nome': 'ativo'}, {'nome': 'baixado'}, {'nome': 'estornado'}]
movimento_patrimonio_tipo_itens = [{'nome': 'pendencia'}, {'nome': 'transferencia'}, {'nome': 'baixa'}, {'nome': 'estorno'}]
movimento_almaxorifado_entrada_tipo_itens = [{'nome': 'entrada'}, {'nome': 'requisicao_uo_material'}, {'nome': 'devolucao'}]
movimento_almaxorifado_saida_tipo_itens = [{'nome': 'requisicao_uo_material'}, {'nome': 'requisicao_user_material'}]
# contrato_tipo_itens = [{'descricao':u'Despesa'}, {'descricao':u'Receita'},]

categoria_material_consumo_itens = [
    {'codigo': '33390.30.01'.split('.')[-1], 'nome': 'COMBUSTIVEIS E LUBRIFICANTES AUTOMOTIVOS'},
    {'codigo': '33390.30.02'.split('.')[-1], 'nome': 'COMBUSTIVEIS E LUBRIFICANTES DE AVIACAO'},
    {'codigo': '33390.30.03'.split('.')[-1], 'nome': 'COMBUSTIVEIS E LUBRIF. P/ OUTRAS FINALIDADES'},
    {'codigo': '33390.30.04'.split('.')[-1], 'nome': 'GAS E OUTROS MATERIAIS ENGARRAFADOS'},
    {'codigo': '33390.30.05'.split('.')[-1], 'nome': 'EXPLOSIVOS E MUNICOES'},
    {'codigo': '33390.30.06'.split('.')[-1], 'nome': 'ALIMENTOS PARA ANIMAIS'},
    {'codigo': '33390.30.07'.split('.')[-1], 'nome': 'GENEROS DE ALIMENTACAO'},
    {'codigo': '33390.30.08'.split('.')[-1], 'nome': 'ANIMAIS PARA PESQUISA E ABATE'},
    {'codigo': '33390.30.09'.split('.')[-1], 'nome': 'MATERIAL FARMACOLOGICO'},
    {'codigo': '33390.30.10'.split('.')[-1], 'nome': 'MATERIAL ODONTOLOGICO'},
    {'codigo': '33390.30.11'.split('.')[-1], 'nome': 'MATERIAL QUIMICO'},
    {'codigo': '33390.30.12'.split('.')[-1], 'nome': 'MATERIAL DE COUDELARIA OU DE USO ZOOTECNICO'},
    {'codigo': '33390.30.13'.split('.')[-1], 'nome': 'MATERIAL DE CACA E PESCA'},
    {'codigo': '33390.30.14'.split('.')[-1], 'nome': 'MATERIAL EDUCATIVO E ESPORTIVO'},
    {'codigo': '33390.30.15'.split('.')[-1], 'nome': 'MATERIAL P/ FESTIVIDADES E HOMENAGENS'},
    {'codigo': '33390.30.16'.split('.')[-1], 'nome': 'MATERIAL DE EXPEDIENTE'},
    {'codigo': '33390.30.17'.split('.')[-1], 'nome': 'MATERIAL DE PROCESSAMENTO DE DADOS'},
    {'codigo': '33390.30.18'.split('.')[-1], 'nome': 'MATERIAIS E MEDICAMENTOS P/ USO VETERINARIO'},
    {'codigo': '33390.30.19'.split('.')[-1], 'nome': 'MATERIAL DE ACONDICIONAMENTO E EMBALAGEM'},
    {'codigo': '33390.30.20'.split('.')[-1], 'nome': 'MATERIAL DE CAMA, MESA E BANHO'},
    {'codigo': '33390.30.21'.split('.')[-1], 'nome': 'MATERIAL DE COPA E COZINHA'},
    {'codigo': '33390.30.22'.split('.')[-1], 'nome': 'MATERIAL DE LIMPEZA E PROD. DE HIGIENIZACAO'},
    {'codigo': '33390.30.23'.split('.')[-1], 'nome': 'UNIFORMES, TECIDOS E AVIAMENTOS'},
    {'codigo': '33390.30.24'.split('.')[-1], 'nome': 'MATERIAL P/ MANUT.DE BENS IMOVEIS/INSTALACOES'},
    {'codigo': '33390.30.25'.split('.')[-1], 'nome': 'MATERIAL P/ MANUTENCAO DE BENS MOVEIS'},
    {'codigo': '33390.30.26'.split('.')[-1], 'nome': 'MATERIAL ELETRICO E ELETRONICO'},
    {'codigo': '33390.30.27'.split('.')[-1], 'nome': 'MATERIAL DE MANOBRA E PATRULHAMENTO'},
    {'codigo': '33390.30.28'.split('.')[-1], 'nome': 'MATERIAL DE PROTECAO E SEGURANCA'},
    {'codigo': '33390.30.29'.split('.')[-1], 'nome': 'MATERIAL P/ AUDIO, VIDEO E FOTO'},
    {'codigo': '33390.30.30'.split('.')[-1], 'nome': 'MATERIAL PARA COMUNICACOES'},
    {'codigo': '33390.30.31'.split('.')[-1], 'nome': 'SEMENTES, MUDAS DE PLANTAS E INSUMOS'},
    {'codigo': '33390.30.32'.split('.')[-1], 'nome': 'SUPRIMENTO DE AVIACAO'},
    {'codigo': '33390.30.33'.split('.')[-1], 'nome': 'MATERIAL P/ PRODUCAO INDUSTRIAL'},
    {'codigo': '33390.30.34'.split('.')[-1], 'nome': 'SOBRESSAL. MAQ.E MOTORES NAVIOS E EMBARCACOES'},
    {'codigo': '33390.30.35'.split('.')[-1], 'nome': 'MATERIAL LABORATORIAL'},
    {'codigo': '33390.30.36'.split('.')[-1], 'nome': 'MATERIAL HOSPITALAR'},
    {'codigo': '33390.30.37'.split('.')[-1], 'nome': 'SOBRESSALENTES DE ARMAMENTO'},
    {'codigo': '33390.30.38'.split('.')[-1], 'nome': 'SUPRIMENTO DE PROTECAO AO VOO'},
    {'codigo': '33390.30.39'.split('.')[-1], 'nome': 'MATERIAL P/ MANUTENCAO DE VEICULOS'},
    {'codigo': '33390.30.40'.split('.')[-1], 'nome': 'MATERIAL BIOLOGICO'},
    {'codigo': '33390.30.41'.split('.')[-1], 'nome': 'MATERIAL P/ UTILIZACAO EM GRAFICA'},
    {'codigo': '33390.30.42'.split('.')[-1], 'nome': 'FERRAMENTAS'},
    {'codigo': '33390.30.43'.split('.')[-1], 'nome': 'MATERIAL P/ REABILITACAO PROFISSIONAL'},
    {'codigo': '33390.30.44'.split('.')[-1], 'nome': 'MATERIAL DE SINALIZACAO VISUAL E OUTROS'},
    {'codigo': '33390.30.45'.split('.')[-1], 'nome': 'MATERIAL TECNICO P/ SELECAO E TREINAMENTO'},
    {'codigo': '33390.30.46'.split('.')[-1], 'nome': 'MATERIAL BIBLIOGRAFICO'},
    {'codigo': '33390.30.47'.split('.')[-1], 'nome': 'AQUISICAO DE SOFTWARES DE BASE'},
    {'codigo': '33390.30.48'.split('.')[-1], 'nome': 'BENS MOVEIS NAO ATIVAVEIS'},
    {'codigo': '33390.30.49'.split('.')[-1], 'nome': 'BILHETES DE PASSAGEM'},
    {'codigo': '33390.30.50'.split('.')[-1], 'nome': 'BANDEIRAS, FLAMULAS E INSIGNIAS'},
    {'codigo': '33390.30.51'.split('.')[-1], 'nome': 'DISCOTECAS E FILMOTECAS NAO IMOBILIZAVEL'},
    {'codigo': '33390.30.52'.split('.')[-1], 'nome': 'MATERIAL DE CARATER SECRETO OU RESERVADO'},
    {'codigo': '33390.30.53'.split('.')[-1], 'nome': 'MATERIAL METEOROLOGICO'},
    {'codigo': '33390.30.54'.split('.')[-1], 'nome': 'MATERIAL P/MANUT.CONSERV.DE ESTRADAS E VIAS'},
    {'codigo': '33390.30.55'.split('.')[-1], 'nome': 'SELOS PARA CONTROLE FISCAL'},
    {'codigo': '33390.30.84'.split('.')[-1], 'nome': 'INTEGRACAO DADOS ESTADOS E MUNICIPIOS - SAFEM'},
    {'codigo': '33390.30.96'.split('.')[-1], 'nome': 'MATERIAL DE CONSUMO - PAGTO ANTECIPADO'},
]

carga_inicial_classes = [
    {'app': 'almoxarifado', 'classe': 'MovimentoAlmoxEntradaTipo', 'tabela': movimento_almaxorifado_entrada_tipo_itens},
    {'app': 'almoxarifado', 'classe': 'MovimentoAlmoxSaidaTipo', 'tabela': movimento_almaxorifado_saida_tipo_itens},
    {'app': 'almoxarifado', 'classe': 'CategoriaMaterialConsumo', 'tabela': categoria_material_consumo_itens},
    {'app': 'almoxarifado', 'classe': 'LicitacaoTipo', 'tabela': licitacao_tipo_itens},
    {'app': 'almoxarifado', 'classe': 'MaterialTipo', 'tabela': material_tipo_itens},
    {'app': 'almoxarifado', 'classe': 'EntradaTipo', 'tabela': entrada_tipo_itens},
    {'app': 'patrimonio', 'classe': 'BaixaTipo', 'tabela': baixa_tipo_itens},
    {'app': 'patrimonio', 'classe': 'InventarioStatus', 'tabela': inventario_status_itens},
    {'app': 'patrimonio', 'classe': 'MovimentoPatrimTipo', 'tabela': movimento_patrimonio_tipo_itens},
    # {'app':'contratos', 'classe':'ContratoTipo', 'tabela':contrato_tipo_itens}
]


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        countGlobal = 0
        for carga in carga_inicial_classes:
            cls = apps.get_model(carga['app'], carga['classe'])
            if cls is None:
                print(('Erro ao importar ', carga['app'], '.models.', carga['classe']))
            else:
                print(('Iniciando carga de ', carga['classe'], '...'))
                countLocal = 0
                for item in carga['tabela']:
                    try:
                        cls.objects.get_or_create(**item)
                    except Exception as e:
                        print((e, item))
                    countLocal = countLocal + 1
                print(('Foram inseridos ', countLocal, ' itens.'))
                countGlobal = countGlobal + countLocal
        print('...')
        print(('Fim da carga inicial, foram incluidos ', countGlobal, ' itens.'))
