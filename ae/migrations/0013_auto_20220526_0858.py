# Generated by Django 3.2.5 on 2022-05-26 08:58

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('comum', '0040_auto_20220510_1439'),
        ('ae', '0012_auto_20220408_0806'),
    ]

    operations = [
        migrations.AddField(
            model_name='agendamentorefeicao',
            name='cancelado',
            field=models.BooleanField(default=False, verbose_name='Cancelado'),
        ),
        migrations.AddField(
            model_name='agendamentorefeicao',
            name='cancelado_em',
            field=djtools.db.models.DateTimeFieldPlus(null=True, verbose_name='Cancelado em'),
        ),
        migrations.AddField(
            model_name='agendamentorefeicao',
            name='cancelado_por',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='agendamentorefeicao_cancelado_por', to='comum.vinculo', verbose_name='Cancelado Por'),
        ),
    ]
