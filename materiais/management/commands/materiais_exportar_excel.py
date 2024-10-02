# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from materiais.models import Material


class Command(BaseCommandPlus):
    def handle(self, *args, **options):

        import xlwt
        import tempfile

        book = xlwt.Workbook(encoding="utf-8")
        sheet = book.add_sheet("Materiais")
        count = 0
        sheet.write(count, 0, 'ID')
        sheet.write(count, 1, 'CATMAT')
        sheet.write(count, 2, 'DESCRIÇÃO')
        sheet.write(count, 3, 'ID CATEGORIA')
        sheet.write(count, 4, 'CATEGORIA')
        sheet.write(count, 5, 'UNIDADE MEDIDA')
        sheet.write(count, 6, 'TAGS')
        count += 1
        for material in Material.objects.all():
            tags = []
            for tag in material.tags.all():
                tags.append(tag.descricao)

            sheet.write(count, 0, (material.id))
            sheet.write(count, 1, (material.codigo_catmat))
            sheet.write(count, 2, (material.especificacao))
            sheet.write(count, 3, (material.categoria.codigo_completo))
            sheet.write(count, 4, (material.categoria.descricao))
            sheet.write(count, 5, (material.unidade_medida.descricao))
            sheet.write(count, 6, (''.join(tags)))
            count += 1

        tmp = tempfile.NamedTemporaryFile('w+b', delete=False)
        print((tmp.name))
        book.save(tmp)
