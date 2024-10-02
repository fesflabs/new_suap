from cnpq.models import CurriculoVittaeLattes
from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):

    def handle(self, *args, **options):
        for registro in CurriculoVittaeLattes.objects.filter(vinculo__isnull=False):
            data_inicio = registro.vinculo.relacionamento.calcula_inicio_exercicio_na_instituicao
            data_fim = registro.vinculo.relacionamento.calcula_fim_servico_na_instituicao
            registro.data_inicio_exercicio = data_inicio
            registro.data_fim_exercicio = data_fim
            if data_inicio:
                registro.ano_inicio_exercicio = data_inicio.year
            if data_fim:
                registro.ano_fim_exercicio = data_fim.year
            registro.save()
