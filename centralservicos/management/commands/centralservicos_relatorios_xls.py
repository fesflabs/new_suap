# -*- coding: utf-8 -*-

import os

import xlwt
from django.conf import settings

from centralservicos.models import AtendimentoAtribuicao, Chamado
from djtools.management.commands import BaseCommandPlus
from djtools.templatetags.filters import format_
from djtools.utils import human_str

"""
python manage.py centralservicos_relatorios_xls
"""


class Command(BaseCommandPlus):
    def chamados_abertos(self, ano, grupos):
        atendimentos = AtendimentoAtribuicao.objects.filter(grupo_atendimento__pk__in=grupos, cancelado_em__isnull=True)
        lista = Chamado.objects.filter(aberto_em__year=ano, pk__in=atendimentos.values('chamado'))

        rows = [['#', 'Chamado', 'Atendente (Nome)', 'Atendente (Login)', 'Grupo Serviço', 'Serviço', 'Aberto Em']]
        count = 0
        for chamado in lista:
            count += 1
            atendente = chamado.get_atendente_do_chamado()
            if atendente:
                nome = atendente.pessoafisica.nome
                username = atendente.username
            else:
                nome = ''
                username = ''
            row = [
                count,
                format_(chamado.id),
                format_(nome),
                format_(username),
                format_(chamado.servico.grupo_servico.nome),
                format_(chamado.servico.nome),
                format_(chamado.aberto_em),
            ]
            rows.append(row)

        file_path = 'centralservicos/fixtures/chamados_abertos{}.xls'.format(ano)
        file_path = os.path.join(settings.BASE_DIR, file_path)
        print(file_path)

        wb = xlwt.Workbook(encoding='iso8859-1')
        sheet = wb.add_sheet("planilha1")

        for row_idx, row in enumerate(rows):
            row = [human_str(i, encoding='iso8859-1', blank='-') for i in row]
            for col_idx, col in enumerate(row):
                sheet.write(row_idx, col_idx, label=col)

        wb.save(file_path)

    def handle(self, *args, **options):
        grupos = [2, 4, 10]
        self.chamados_abertos(2017, grupos)
