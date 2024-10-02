from suap import celery_app


def get_sync_task_name():
    return "Syncronizar Laboratórios Guacamole"


@celery_app.task(bind=True)
def sync_labs_guacamole(self):
    from labfisico.models import AgendamentoLabFisico
    from djtools.utils import get_datetime_now
    agora = get_datetime_now()

    inativos = AgendamentoLabFisico.objects.inativos().filter(data_hora_inicio__lte=agora, data_hora_fim__gte=agora)
    for agendamento in inativos:
        print('[Celery-SUAP] Ativando agendamentos dos laboratórios físicos. Request: {0!r}'.format(self.request))
        agendamento.ativar()
        agendamento.save()

    ativos = AgendamentoLabFisico.objects.ativos().filter(data_hora_fim__lte=agora)
    for agendamento in ativos:
        print('[Celery-SUAP] Encerrrando agendamentos dos laboratórios físicos. Request: {0!r}'.format(self.request))
        agendamento.inativar()
        agendamento.save()


def finalizar_agendamentos_guacamole():
    from labfisico.models import SolicitacaoLabFisico
    solicitacoes = SolicitacaoLabFisico.objects.expiradas()
    for solicitacao in solicitacoes:
        solicitacao.finalizar()
        solicitacao.save()


def load_tasks_schedule():
    from django_celery_beat.models import PeriodicTask, IntervalSchedule
    every_2_minutes, _ = IntervalSchedule.objects.get_or_create(
        every=2, period=IntervalSchedule.MINUTES,
    )

    PeriodicTask.objects.update_or_create(
        task="labfisico.tasks.sync_labs_guacamole",
        name=get_sync_task_name(),
        defaults=dict(
            queue='beat',
            interval=every_2_minutes,
            expire_seconds=60,  # If not run within 60 seconds, forget it; another one will be scheduled soon.
        ),
    )
