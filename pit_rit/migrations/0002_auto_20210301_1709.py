# Generated by Django 2.2.16 on 2021-03-01 17:09

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('pit_rit', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='configuracaoatividadedocente',
            name='portaria_normativa',
            field=djtools.db.models.FileFieldPlus(upload_to='edu/configuracao_atividade_docente/', verbose_name='Portaria Normativa'),
        ),
    ]
