# Generated by Django 2.2.10 on 2020-04-15 12:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('plan_estrategico', '0023_merge_20200326_1404')]

    operations = [
        migrations.AddField(
            model_name='unidadegestora', name='recurso_total', field=models.BooleanField(default=False, verbose_name='Pode Alocar 100% do Recurso na Etapa Especial?')
        )
    ]
