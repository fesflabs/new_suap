# Generated by Django 2.2.16 on 2021-01-14 10:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eventos', '0009_merge_20210104_0952'),
    ]

    operations = [
        migrations.AddField(
            model_name='evento',
            name='registrar_presenca_online',
            field=models.BooleanField(default=False, help_text='Marque essa opção caso deseje que os próprios inscritos possam registrar presença através de um e-mail enviado pelo coordenador/organizador.', verbose_name='Registrar Presença Online'),
        ),
    ]