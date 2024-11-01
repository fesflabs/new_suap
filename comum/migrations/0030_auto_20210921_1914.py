# Generated by Django 3.2.5 on 2021-09-21 19:14

from django.db import migrations
import django.db.models.deletion
import django.utils.timezone
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('comum', '0029_alter_sessioninfo_device'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='sessioninfo',
            name='agent',
        ),
        migrations.RemoveField(
            model_name='sessioninfo',
            name='ip_address',
        ),
        migrations.RemoveField(
            model_name='sessioninfo',
            name='user',
        ),
        migrations.AddField(
            model_name='registronotificacao',
            name='data_permite_excluir',
            field=djtools.db.models.DateTimeFieldPlus(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='registronotificacao',
            name='data_permite_marcar_lida',
            field=djtools.db.models.DateTimeFieldPlus(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='sessioninfo',
            name='device',
            field=djtools.db.models.ForeignKeyPlus(default=1, on_delete=django.db.models.deletion.CASCADE, to='comum.device'),
            preserve_default=False,
        ),
    ]
