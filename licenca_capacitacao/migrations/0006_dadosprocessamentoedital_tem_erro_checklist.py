# Generated by Django 2.2.16 on 2021-05-13 10:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('licenca_capacitacao', '0005_auto_20210510_1449'),
    ]

    operations = [
        migrations.AddField(
            model_name='dadosprocessamentoedital',
            name='tem_erro_checklist',
            field=models.NullBooleanField(verbose_name='Erro no checklist'),
        ),
    ]