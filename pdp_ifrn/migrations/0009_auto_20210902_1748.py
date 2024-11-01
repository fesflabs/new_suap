# Generated by Django 3.2.5 on 2021-09-02 17:48

from django.db import migrations, models
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('pdp_ifrn', '0008_auto_20210902_1727'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicostatusresposta',
            name='status',
            field=djtools.db.models.CharFieldPlus(default=(('pendente', 'Pendente'), ('deferida', 'Deferida pela Comissão Local'), ('aprovada', 'Aprovada pela Comissão Sistêmica'), ('homologada', 'Homologada pelo Reitor')), max_length=10, verbose_name='Situação'),
        ),
        migrations.AlterField(
            model_name='resposta',
            name='justificativa_necessidade',
            field=models.TextField(help_text='<strong>OBS 1: </strong> indique os resultados organizacionais a serem alcançados; <strong>OBS 2: </strong> indique comportamento e/ou resultados pessoais que os servidores conseguirão apresentar com a realização da ação de desenvolvimento;', max_length=200, verbose_name='Que resultado essa ação de desenvolvimento trará?'),
        ),
    ]
