import celery
import json
import datetime
from suap import celery_app
from django.utils.timezone import get_current_timezone


class BaseTaskWithRetry(celery.Task):
    autoretry_for = (Exception, KeyError)
    retry_kwargs = {'max_retries': 5}
    retry_backoff = True


@celery_app.task(bind=True, base=BaseTaskWithRetry)
def sync_labs_vdi(self):
    from labvirtual.models import AgendamentoLabVirtual
    from djtools.utils import get_datetime_now
    now = get_datetime_now()
    #
    print('[Celery-SUAP] Verificando agendamentos............')
    agendamentos = AgendamentoLabVirtual.objects.inativos().filter(data_hora_inicio__lte=now, data_hora_fim__gte=now)
    for agendamento in agendamentos:
        print('[Celery-SUAP] Ativar Agendamento Request: {0!r}'.format(self.request))
        agendamento.ativar()
        agendamento.save()
    #
    agendamentos = AgendamentoLabVirtual.objects.ativos().filter(data_hora_fim__lte=now)
    for agendamento in agendamentos:
        print('[Celery-SUAP] Desativando Agendamento Request: {0!r}'.format(self.request))
        agendamento.inativar()
        agendamento.save()

    #
    agendamentos = AgendamentoLabVirtual.objects.ativos().filter(data_hora_fim__lte=now + datetime.timedelta(minutes=5))
    for agendamento in agendamentos:
        print('[Celery-SUAP] Enviando notificação de expiração: {0!r}'.format(self.request))
        eta = agendamento.data_hora_fim - now
        msg = f"A sua sessão vai expirar em {eta} minutos. Salve o seu trabalho."
        agendamento.enviar_notificacao(msg)


@celery_app.task(bind=True, base=BaseTaskWithRetry)
def ativar_agendamento(self, id):
    from labvirtual.models import AgendamentoLabVirtual
    try:
        print('[Celery-SUAP] Ativar agendamento {0}: {1!r}'.format(id, self.request))
        agendamento = AgendamentoLabVirtual.objects.get(pk=id)
        agendamento.ativar()
        agendamento.save()
    except Exception as e:
        print('[Erro: Celery-SUAP] Ativar agendamento {0}: {1!r}: {2}'.format(id, self.request, str(e)))
        raise e


@celery_app.task(bind=True, base=BaseTaskWithRetry)
def notificar_agendamento(self, id):
    from labvirtual.models import AgendamentoLabVirtual
    try:
        print('[Celery-SUAP] Notificar agendamento {0}: {1!r}'.format(id, self.request))
        agendamento = AgendamentoLabVirtual.objects.get(pk=id)
        msg = "A sua sessão vai expirar em 5 minutos. Salve o seu trabalho."
        agendamento.enviar_notificacao(msg)
    except Exception as e:
        print('[Erro: Celery-SUAP] Enviar mensagem agendamento {0}: {1!r}: {2}'.format(id, self.request, str(e)))
        raise e


@celery_app.task(bind=True, base=BaseTaskWithRetry)
def desativar_agendamento(self, id):
    from labvirtual.models import AgendamentoLabVirtual
    try:
        print('[Celery-SUAP] Inativar agendamento {0}: {1!r}'.format(id, self.request))
        agendamento = AgendamentoLabVirtual.objects.get(pk=id)
        agendamento.inativar()
        agendamento.save()
    except Exception as e:
        print('[Erro: Celery-SUAP] Inativar agendamento {0}: {1!r}: {2}'.format(id, self.request, str(e)))
        raise e


def criar_agendamento(agendamento):
    from django_celery_beat.models import PeriodicTask, ClockedSchedule
    five_minute = datetime.timedelta(minutes=5)

    start = agendamento.data_hora_inicio
    end = agendamento.data_hora_fim
    warn_time = agendamento.data_hora_fim - five_minute

    enable_at, _ = ClockedSchedule.objects.get_or_create(clocked_time=start)
    disable_at, _ = ClockedSchedule.objects.get_or_create(clocked_time=end)
    warn_at, _ = ClockedSchedule.objects.get_or_create(clocked_time=warn_time)

    #
    PeriodicTask.objects.update_or_create(
        task="labvirtual.tasks.ativar_agendamento",
        name=f"Ativar Agendamento #{agendamento.pk}",
        defaults=dict(
            clocked=enable_at,
            kwargs=json.dumps({"id": str(agendamento.pk)}),
            one_off=True
        ),
    )

    PeriodicTask.objects.update_or_create(
        task="labvirtual.tasks.notificar_agendamento",
        name=f"Enviar notificação de encerramento do Agendamento #{agendamento.pk}",
        defaults=dict(
            clocked=warn_at,
            kwargs=json.dumps({"id": str(agendamento.pk)}),
            one_off=True
        )
    )

    PeriodicTask.objects.update_or_create(
        task="labvirtual.tasks.desativar_agendamento",
        name=f"Desativar Agendamento #{agendamento.pk}",
        defaults=dict(
            clocked=disable_at,
            kwargs=json.dumps({"id": str(agendamento.pk)}),
            one_off=True
        )
    )


def load_tasks_schedule():
    from django_celery_beat.models import PeriodicTask, IntervalSchedule
    every_5_minutes, _ = IntervalSchedule.objects.get_or_create(
        every=1, period=IntervalSchedule.MINUTES,
    )
    #
    PeriodicTask.objects.update_or_create(
        task="labvirtual.tasks.sync_labs_vdi",
        name="Syncronizar Laboratórios do Horizon",
        defaults=dict(
            interval=every_5_minutes,
            expire_seconds=60,  # If not run within 60 seconds, forget it; another one will be scheduled soon.
        ),
    )


def finalizar_agendamentos_vdi():
    from labvirtual.models import SolicitacaoLabVirtual
    solicitacoes = SolicitacaoLabVirtual.objects.expiradas()
    for solicitacao in solicitacoes:
        solicitacao.finalizar()
        solicitacao.save()


@celery_app.task(bind=True, base=BaseTaskWithRetry)
def clocked_task(self):
    print('[Celery-SUAP] Clocked Task {0}: {1!r}'.format(id, self.request))


def make_localtime_aware(value, timezone=None):
    from django.utils.timezone import make_aware
    timezone = timezone or get_current_timezone()
    return make_aware(value, timezone)


def to_celery(dt):
    from celery.utils.time import to_utc
    now_in_utc = to_utc(dt)
    return now_in_utc


def clocked_schedule_test():
    from django_celery_beat.models import PeriodicTask, ClockedSchedule
    from djtools.utils import get_datetime_now

    now = get_datetime_now()
    start_time = make_localtime_aware(now + datetime.timedelta(minutes=2))
    expire_at = make_localtime_aware(now + datetime.timedelta(minutes=12))
    #
    enable_at, _ = ClockedSchedule.objects.update_or_create(clocked_time=start_time)
    print(f'clocked Test: {start_time} - {expire_at}')
    #
    obj = PeriodicTask.objects.update_or_create(
        task="labvirtual.tasks.clocked_task",
        name="Clocked Test",
        defaults=dict(
            clocked=enable_at,
            one_off=True,
            enabled=True,
            expires=expire_at
        ),
    )
    return obj
