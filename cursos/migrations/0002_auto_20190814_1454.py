# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-08-14 14:54


from django.db import migrations
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [('protocolo', '0001_initial'), ('comum', '0002_auto_20190814_1443'), ('cursos', '0001_initial'), ('rh', '0001_initial')]

    operations = [
        migrations.AddField(
            model_name='curso', name='processos', field=djtools.db.models.ManyToManyFieldPlus(blank=True, to='protocolo.Processo', verbose_name='Processos relacionados')
        ),
        migrations.AddField(model_name='curso', name='responsaveis', field=djtools.db.models.ManyToManyFieldPlus(blank=True, to='rh.Servidor', verbose_name='Responsáveis')),
        migrations.AddField(
            model_name='cotaextra', name='ano', field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='comum.Ano', verbose_name='Ano')
        ),
        migrations.AddField(
            model_name='cotaextra', name='processos', field=djtools.db.models.ManyToManyFieldPlus(blank=True, to='protocolo.Processo', verbose_name='Processos relacionados')
        ),
        migrations.AddField(
            model_name='cotaextra', name='servidor', field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='rh.Servidor', verbose_name='Servidor')
        ),
        migrations.AddField(
            model_name='cotaanualservidor', name='ano_pagamento', field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='comum.Ano')
        ),
        migrations.AddField(
            model_name='cotaanualservidor',
            name='horas_permitidas',
            field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='cursos.HorasPermitidas'),
        ),
        migrations.AddField(
            model_name='cotaanualservidor', name='vinculo', field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='comum.Vinculo')
        ),
        migrations.AlterUniqueTogether(name='horastrabalhadas', unique_together=set([('curso', 'cota_anual_servidor', 'mes_pagamento', 'atividade', 'atividade_valor_hora')])),
        migrations.AlterUniqueTogether(name='curso', unique_together=set([('descricao', 'ano_pagamento')])),
        migrations.AlterUniqueTogether(name='cotaanualservidor', unique_together=set([('vinculo', 'ano_pagamento')])),
    ]