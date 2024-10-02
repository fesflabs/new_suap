import math
from datetime import datetime, timedelta
import random
from django.conf import settings
from djtools.testutils import running_tests
from djtools.db import models
from djtools.utils import send_notification
from djtools.storages.utils import upload_temporary_file
import uuid


class Task(models.ModelPlus):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    type = models.CharFieldPlus(verbose_name='Tipo')
    user = models.ForeignKeyPlus('comum.User', verbose_name='Usuário', null=True)
    message = models.CharFieldPlus(verbose_name='Mensagem', null=True)
    file = models.CharFieldPlus(verbose_name='Arquivo', null=True)
    total = models.IntegerField(verbose_name='Total', default=0)
    partial = models.IntegerField(verbose_name='Parcial', default=0)
    error = models.TextField(verbose_name='Erro', null=True)
    start = models.DateTimeFieldPlus(verbose_name='Início', auto_now=True)
    end = models.DateTimeFieldPlus(verbose_name='Fim', null=True)
    notify = models.BooleanField(default=False)
    url = models.CharFieldPlus(verbose_name='URL de Redirecionamento', max_length=524, default='')

    objects = models.Manager()

    class History:
        disabled = True

    class Meta:
        verbose_name = 'Tarefa'
        verbose_name_plural = 'Tarefas'

    def get_absolute_url(self):
        return f'/djtools/view_task/{self.pk}/'

    @property
    def percent(self):
        return math.floor(self.partial * 100 / (self.total or self.partial or 1))

    def count(self, *iterables):
        for iterable in iterables:
            self.total += len(iterable)
        Task.objects.filter(pk=self.pk).update(total=self.total)

    def start_progress(self, total=100):
        self.total = total
        Task.objects.filter(pk=self.pk).update(total=total)

    def update_progress(self, percent):
        self.partial = percent
        Task.objects.filter(pk=self.pk).update(partial=percent)

    def iterate(self, iterable):
        if not self.total:
            self.total = len(iterable)
            Task.objects.filter(pk=self.pk).update(total=self.total)
        partial = self.partial
        previous_percent = 0
        for i, obj in enumerate(iterable):
            self.partial = partial + i
            each_five_percent = math.floor(self.partial * 20 / self.total)
            if previous_percent < each_five_percent or i == self.total:
                previous_percent = each_five_percent
                Task.objects.filter(pk=self.pk).update(partial=self.partial)
            yield obj

    def finalize(self, message, url='', error=False, file_path=None):
        if not self.url:
            self.url = url
        if error:
            self.error = message
            self.message = f'Ocorreu um <a href="{self.get_absolute_url()}">erro</a> '
        else:
            self.partial = self.total
            self.message = message
            if file_path:
                self.file = upload_temporary_file(file_path)
        self.end = datetime.now()
        Task.objects.filter(pk=self.pk).update(error=self.error, message=self.message, file=self.file, end=self.end, partial=self.partial, url=self.url)
        obj = Task.objects.filter(pk=self.pk).first()
        if obj and obj.notify:
            self.send_notification()

    def get_progress(self):
        progress = 0
        if self.total:
            progress = int(self.partial * 100 / self.total)
        return progress > 100 and 100 or progress

    def send_notification(self):
        titulo = f'[SUAP] Resultado da Execução do Tarefa {self.id}'
        url = f'{settings.SITE_URL}/djtools/view_task/{self.id}/'
        mensagem = f'<h1>Resultado da Execução da Tarefa #{self.id}</h1><b>Tarefa: {self.type}<p>O resultado está disponível no endereço: <a href="{url}">{url}</a>.</p>'
        send_notification(titulo, mensagem, settings.DEFAULT_FROM_EMAIL, [self.user.get_vinculo()],
                          categoria='Resultado da Execução de Tarefa')

    def __str__(self):
        return f'Tarefa #{self.id}'


class TwoFactorAuthenticationCode(models.ModelPlus):
    user = models.CurrentUserField(verbose_name='Usuário')
    email = models.CharFieldPlus(verbose_name='E-mail')
    expires = models.DateTimeFieldPlus()
    code = models.CharFieldPlus(verbose_name='Código', max_length=6)

    class History:
        disabled = True

    class Meta:
        verbose_name = 'Código de Autenticação'
        verbose_name_plural = 'Códigos de Autenticação'

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.email = self.user.get_vinculo().pessoa.email_secundario or ''
        if running_tests():
            self.code = 123456
        else:
            self.code = random.randint(1, 1000001)
        self.expires = datetime.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)


class APICache(models.ModelPlus):
    filtro_api = models.JSONField(verbose_name='Filtros de API')
    resultado = models.JSONField()
    data_expiracao = models.DateTimeFieldPlus()

    class Meta:
        abstract = True

    @classmethod
    def get(cls, filtro_api):
        obj = cls.objects.filter(filtro_api=filtro_api).first()
        if obj and obj.data_expiracao < datetime.now():
            obj.delete()
            obj = None
        return obj


class ConsultaCidadaoCache(APICache):
    cpf_operador = models.CharFieldPlus('Cpf do Operador')

    class History:
        disabled = True

    def __str__(self):
        return f'{self.filtro_api} - {self.resultado}'
