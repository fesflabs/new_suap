# Generated by Django 2.2.10 on 2020-03-05 10:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('plan_estrategico', '0017_atividadeetapa_valor_rateio')]

    operations = [migrations.AddField(model_name='etapaprojetoplanoatividade', name='tipo_especial', field=models.BooleanField(default=False))]