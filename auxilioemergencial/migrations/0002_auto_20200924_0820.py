# Generated by Django 2.2.10 on 2020-09-24 08:20

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('auxilioemergencial', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='inscricaodispositivo',
            name='documentacao_atualizada_em',
            field=djtools.db.models.DateTimeFieldPlus(null=True, verbose_name='Documentação Atualizada em'),
        ),
        migrations.AddField(
            model_name='inscricaointernet',
            name='documentacao_atualizada_em',
            field=djtools.db.models.DateTimeFieldPlus(null=True, verbose_name='Documentação Atualizada em'),
        ),
        migrations.AddField(
            model_name='inscricaomaterialpedagogico',
            name='documentacao_atualizada_em',
            field=djtools.db.models.DateTimeFieldPlus(null=True, verbose_name='Documentação Atualizada em'),
        ),
    ]