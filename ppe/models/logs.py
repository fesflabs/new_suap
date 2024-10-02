import sys

from django.conf import settings

from djtools.db import models
from django.dispatch.dispatcher import receiver

from django.db.models.signals import pre_save, post_save, pre_delete
from djtools.templatetags.filters import format_money, format_datetime, format_
from djtools.utils import normalizar_nome_proprio
from comum.utils import tl


class Log(models.ModelPlus):
    CADASTRO = 1
    EDICAO = 2
    EXCLUSAO = 3
    VISUALIZACAO = 4

    TIPO_CHOICES = [[CADASTRO, 'Cadastro'], [EDICAO, 'Edição'], [EXCLUSAO, 'Exclusão'], [VISUALIZACAO, 'Visualização']]

    user = models.ForeignKeyPlus('comum.User', null=True, on_delete=models.SET_NULL , related_name='logs_user_ppe')
    trabalhador_educando = models.ForeignKeyPlus('ppe.TrabalhadorEducando', null=True, on_delete=models.SET_NULL)
    dt = models.DateTimeFieldPlus(auto_now=True)
    tipo = models.IntegerField(choices=TIPO_CHOICES)
    descricao = models.CharFieldPlus()
    app = models.CharFieldPlus()
    modelo = models.CharFieldPlus()
    nome_modelo = models.CharFieldPlus()
    ref = models.IntegerField(db_index=True)
    ref_trabalhador_educando = models.IntegerField(null=True, db_index=True)
    ref_curso_turma = models.IntegerField(null=True, db_index=True)

    class History:
        disabled = True

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return "/ppe/log/{:d}/".format(self.pk)

    class Meta:
        verbose_name = 'Log'
        verbose_name_plural = 'Logs'

    def set_up(self, user, tipo, instance, descricao):
        self.user = user
        self.tipo = tipo
        self.descricao = descricao
        self.app = instance._meta.app_label
        self.modelo = instance.__class__.__name__
        self.nome_modelo = instance._meta.verbose_name
        self.ref = instance.pk

        self.ref_curso_turma = None
        if hasattr(instance, 'curso_turma') and instance.curso_turma:
            self.ref_curso_turma = instance.curso_turma.pk
        elif hasattr(instance, 'get_curso_turma') and hasattr(instance.get_curso_turma(), 'pk'):
            self.ref_curso_turma = instance.get_curso_turma().pk

        self.ref_trabalhador_educando = None
        if hasattr(instance, 'trabalhador_educando'):
            self.ref_trabalhador_educando = instance.trabalhador_educando.pk
        elif hasattr(instance, 'get_trabalhador_educando') and hasattr(instance.get_trabalhador_educando(), 'pk'):
            self.ref_trabalhador_educando = instance.get_trabalhador_educando().pk

        self.save()


class RegistroDiferenca(models.ModelPlus):
    log = models.ForeignKeyPlus(Log, null=False)
    valor_anterior = models.TextField()
    valor_atual = models.TextField()
    campo = models.CharFieldPlus(null=False)

    class History:
        disabled = True


class LogPPEModel(models.ModelPlus):
    class Meta:
        abstract = True

    def format(self, value):
        if value in (None, ''):
            return '-'
        elif isinstance(value, bool):
            return value and 'Sim' or 'Não'
        elif value.__class__.__name__ == 'Decimal':
            return format_money(value)
        elif hasattr(value, 'strftime'):
            return format_datetime(value)
        return str(value)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self.__class__, '_if_changed') and not 'test_suap' in sys.argv and not 'test' in sys.argv and settings.USE_EDU_LOG:

            @receiver(pre_save, sender=self.__class__)
            def _if_changed(sender, instance, **kwargs):
                user = tl.get_user()
                user = user and not user.is_anonymous and user or None
                old = instance.__class__.objects.filter(pk=instance.pk).first()
                desc = 'O usuário atualizou {} #{}'.format(instance._meta.verbose_name, instance.pk)
                instance._inserted = True
                if old:
                    instance._inserted = False
                    log = Log()
                    for field in instance._meta.fields:
                        o1 = getattr(old, field.name)
                        o2 = getattr(instance, field.name)
                        v1 = self.format(o1)
                        v2 = self.format(o2)
                        if ((type(o1) == str or type(o2) == str) or not hasattr(o2, '__iter__')) and v1 != v2:
                            log.set_up(user, Log.EDICAO, instance, desc)
                            if not log.id:
                                log.save()
                            RegistroDiferenca.objects.create(valor_anterior=v1, valor_atual=v2, campo=normalizar_nome_proprio(field.verbose_name), log=log)

            @receiver(post_save, sender=self.__class__)
            def _if_inserted(sender, instance, **kwargs):
                if hasattr(instance, '_inserted') and getattr(instance, '_inserted'):
                    user = tl.get_user()
                    user = user and not user.is_anonymous and user or None
                    desc = 'O usuário cadastrou {} #{}'.format(instance._meta.verbose_name, instance.pk)
                    log = Log()
                    log.set_up(user, Log.CADASTRO, instance, desc)
                    log.save()

            @receiver(pre_delete, sender=self.__class__)
            def _if_deleted(sender, instance, **kwargs):
                user = tl.get_user()
                user = user and not user.is_anonymous and user or None
                desc = 'O usuário excluiu {} #{}'.format(instance._meta.verbose_name, instance.pk)
                old = instance.__class__.objects.filter(pk=instance.pk).first()
                if old:
                    log = Log()
                    log.set_up(user, Log.EXCLUSAO, instance, desc)
                    log.save()
                    for field in instance._meta.fields:
                        if not isinstance(field, models.FileField):
                            v1 = str(format_(getattr(old, field.name), html=False))
                            RegistroDiferenca.objects.create(valor_anterior=v1, valor_atual='', campo=normalizar_nome_proprio(field.verbose_name), log=log)

            self.__class__._if_changed = _if_changed
            self.__class__._if_inserted = _if_inserted
            self.__class__._if_deleted = _if_deleted
