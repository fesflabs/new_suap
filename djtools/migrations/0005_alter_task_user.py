# Generated by Django 3.2.5 on 2021-12-17 14:07

import uuid

import django.db.models.deletion
import tqdm
from django.conf import settings
from django.db import migrations
from django.db.models import Count

import djtools.db.models


def atualizar_dados(apps, schema):
    Task = apps.get_model('djtools.Task')
    for task_uuid, count in Task.objects.values_list('uuid').annotate(count=Count('uuid')).filter(count__gt=1):
        for task in tqdm.tqdm(Task.objects.filter(uuid=task_uuid)):
            task.uuid = uuid.uuid4()
            task.save()
        print('\n\n\n')


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('djtools', '0004_auto_20211126_0948'),
    ]

    operations = [
        migrations.RunPython(atualizar_dados),
        migrations.AlterField(
            model_name='task',
            name='user',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Usuário'),
        ),
        migrations.AlterField(
            model_name='task',
            name='uuid',
            field=djtools.db.models.UUIDField(default=uuid.uuid4, unique=True),
        )
    ]
