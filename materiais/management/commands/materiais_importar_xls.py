# -*- coding: utf-8 -*-

from decimal import Decimal

from django.db import transaction

from djtools.management.commands import BaseCommandPlus
from materiais.models import Material, MaterialTag, MaterialCotacao, Categoria


class Command(BaseCommandPlus):
    @transaction.atomic
    def handle(self, *args, **options):
        # cadastra/atualiza material
        def cadastra_material(id_material, catmat, descricao, especificacao, categoria_id, unidade_id, tag_id, p1, o1, p2, o2, p3, o3):

            # se não tem ID, cadastra, se tem, atualiza
            material = None
            inserindo = False

            if id == "" or id == "-":
                inserindo = True
                material = Material()
            else:
                print(("Buscando material... ", int(id)))
                material = Material.objects.get(pk=id_material)

            material.codigo_catmat = catmat
            material.descricao = descricao
            material.especificacao = especificacao
            material.unidade_medida_id = unidade_id

            if categoria_id:
                material.categoria_id = categoria_id

            material.save()

            print(("Procurando tag_id ", int(tag_id)))
            tag = MaterialTag.objects.get(pk=int(tag_id))

            if not inserindo:
                # antes de atualizar limpa as cotações de preços antigas
                print(("Excluindo cotacoes antigas do material ", material.descricao))
                material.materialcotacao_set.all().delete()

            # cadastra/atualiza tags
            material.tags.add(tag)

            # cotação 1?
            if p1:
                print("     <<< Cadastrando cotação 1")
                cotacao = MaterialCotacao()
                cotacao.referencia = o1
                cotacao.valor = Decimal(str(p1))  # sem esse cast ocorre erro em produção (Python 2.6)
                material.materialcotacao_set.add(cotacao)

            # cotação 2?
            if p2:
                print("     <<< Cadastrando cotação 2")
                cotacao = MaterialCotacao()
                cotacao.referencia = o2
                cotacao.valor = Decimal(str(p2))
                material.materialcotacao_set.add(cotacao)

            # cotação 3?
            if p3:
                print("     <<< Cadastrando cotação 3")
                cotacao = MaterialCotacao()
                cotacao.referencia = o3
                cotacao.valor = Decimal(str(p3))
                material.materialcotacao_set.add(cotacao)

        # parâmetros informados?
        if len(args) != 1:
            print("Arquivo XLS não informado.\n")
            print("python manage.py materiais_importar_xls /tmp/arquivo.xls\n")
            return

        # tratando XLS
        arquivo_xls = args[0]
        print(("Importando materiais a partir do arquivo XLS: %s" % args[0]))
        from xlrd import open_workbook

        wb = open_workbook(arquivo_xls)
        plan = wb.sheets()[0]
        print(("Verificando planilha %s..." % str(plan.name)))

        for row in range(1, plan.nrows):
            id = plan.cell(row, 2).value
            catmat = plan.cell(row, 3).value
            descricao = str(plan.cell(row, 4).value).strip()
            especificacao = str(plan.cell(row, 5).value).strip()
            unidade_id = plan.cell(row, 6).value
            tag_id = plan.cell(row, 8).value
            categoria_id = None
            p1 = str(plan.cell(row, 10).value).replace(".", "").replace(",", ".")
            o1 = str(plan.cell(row, 11).value).strip()
            p2 = str(plan.cell(row, 12).value).replace(".", "").replace(",", ".")
            o2 = str(plan.cell(row, 13).value).strip()
            p3 = str(plan.cell(row, 14).value).replace(".", "").replace(",", ".")
            o3 = str(plan.cell(row, 15).value).strip()

            # ajustando CATMAT vazio
            if catmat == "" or catmat == "-":
                catmat = "000000"
            else:
                catmat = str(int(catmat))  # ao importar o xls insere um ".0" no final (float)

            # verificando linhas sem categorias
            if plan.cell(row, 17).value != "":
                categoria_id = Categoria.objects.get(codigo_completo=str(plan.cell(row, 17).value)).pk
            else:
                categoria_id = None
                print(("Categoria nao informada na linha ", row, " / ", descricao))

            print(("Cadastrando item ", row, "... (id: ", str(id), ")"))
            cadastra_material(id, catmat, descricao, especificacao, categoria_id, unidade_id, tag_id, p1, o1, p2, o2, p3, o3)
