# -*- coding: utf-8 -*-
# Generated by Django 1.11.18 on 2019-08-08 14:32
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [('saude', '0003_auto_20190516_1140')]

    operations = [
        migrations.AddField(
            model_name='anexopsicologia',
            name='cadastrado_por_vinculo',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='comum.Vinculo'),
        ),
        migrations.AddField(
            model_name='atividadegrupo', name='vinculos_responsaveis', field=models.ManyToManyField(related_name='vinculos_responsaveis_atividades_grupo', to='comum.Vinculo')
        ),
        migrations.AddField(
            model_name='bloqueioatendimentosaude',
            name='vinculo_paciente',
            field=djtools.db.models.ForeignKeyPlus(
                null=True, on_delete=django.db.models.deletion.CASCADE, related_name='vinculo_paciente_bloqueio_agendamento', to='comum.Vinculo'
            ),
        ),
        migrations.AddField(
            model_name='bloqueioatendimentosaude',
            name='vinculo_profissional',
            field=djtools.db.models.ForeignKeyPlus(
                null=True, on_delete=django.db.models.deletion.CASCADE, related_name='vinculo_profissional_bloqueio_agendamento', to='comum.Vinculo'
            ),
        ),
        migrations.AddField(
            model_name='documentoprontuario',
            name='cadastrado_por_vinculo',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='comum.Vinculo'),
        ),
        migrations.AddField(
            model_name='horarioatendimento',
            name='cadastrado_por_vinculo',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='comum.Vinculo'),
        ),
        migrations.AddField(
            model_name='horarioatendimento',
            name='vinculo_paciente',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='vinculo_paciente_agendamento', to='comum.Vinculo'),
        ),
        migrations.AddField(
            model_name='odontograma',
            name='atendido_por_vinculo',
            field=djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='comum.Vinculo'),
        ),
        migrations.AddField(
            model_name='prontuario',
            name='cadastrado_por_vinculo',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='comum.Vinculo'),
        ),
        migrations.AddField(
            model_name='prontuario',
            name='vinculo',
            field=djtools.db.models.OneToOneFieldPlus(
                null=True, on_delete=django.db.models.deletion.CASCADE, related_name='vinculo_paciente_prontuario', to='comum.Vinculo', verbose_name='V\xednculo'
            ),
        ),
        migrations.AddField(
            model_name='registroadministrativo',
            name='vinculo_profissional',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='comum.Vinculo'),
        ),
        migrations.AlterField(
            model_name='prontuario',
            name='pessoa_fisica',
            field=djtools.db.models.OneToOneFieldPlus(on_delete=django.db.models.deletion.CASCADE, to='rh.PessoaFisica', verbose_name='Pessoa F\xedsica/Matr\xedcula'),
        ),
    ]
