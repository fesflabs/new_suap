# Generated by Django 2.2.10 on 2020-03-09 08:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('plan_estrategico', '0019_origemrecursoprojetoetapa_tipo_especial')]

    operations = [
        migrations.AddField(model_name='planoatividade', name='percentual_reserva_tecnica', field=models.IntegerField(null=True, verbose_name='Percentual da Reserva Técnica'))
    ]