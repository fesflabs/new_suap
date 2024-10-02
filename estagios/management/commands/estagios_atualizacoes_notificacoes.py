import datetime
from dateutil.relativedelta import relativedelta
from djtools.management.commands import BaseCommandPlus
from estagios.models import PraticaProfissional, Aprendizagem, AtividadeProfissionalEfetiva


class Command(BaseCommandPlus):
    def handle(self, *args, **options):

        estagios = PraticaProfissional.objects.filter(data_fim__isnull=True)
        for estagio in estagios:
            try:
                estagio.atualizar_situacoes(salvar=True)
                estagio.verificar_pendencias()
                estagio.verificar_matricula_irregular()
            except Exception:
                print(f'Erro no estágio: {estagio.pk}')

        aprendizagens = Aprendizagem.objects.filter(data_encerramento__isnull=True)
        for aprendizagem in aprendizagens:
            try:
                aprendizagem.verificar_pendencias()
                aprendizagem.verificar_matricula_irregular()
            except Exception:
                print(f'Erro na aprendizagem: {aprendizagem.pk}')

        aprendizagens = aprendizagens | Aprendizagem.objects.filter(
            data_encerramento__isnull=False, data_encerramento__gte=datetime.date.today() - relativedelta(months=1), data_encerramento__lte=datetime.date.today()
        )
        for aprendizagem in aprendizagens:
            try:
                aprendizagem.verificar_envio_relatorio_frequencia()
            except Exception:
                print(f'Erro na notificação da aprendizagem: {aprendizagem.pk}')
        atividades_profissionais_efetivas = AtividadeProfissionalEfetiva.objects.filter(situacao=AtividadeProfissionalEfetiva.EM_ANDAMENTO)
        for ape in atividades_profissionais_efetivas:
            try:
                ape.verificar_matricula_irregular()
            except Exception:
                print(f'Erro na atividade profissional {ape.pk}')
