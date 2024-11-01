# Generated by Django 3.2.5 on 2022-06-08 09:55

from django.db import migrations
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0036_auto_20220405_2129'),
        ('saude', '0018_auto_20220427_1537'),
    ]

    operations = [
        migrations.AlterField(
            model_name='anexopsicologia',
            name='cadastrado_por',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='rh.pessoafisica'),
        ),
        migrations.AlterField(
            model_name='bloqueioatendimentosaude',
            name='paciente',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='paciente_bloqueio_agendamento', to='rh.pessoafisica', verbose_name='Paciente'),
        ),
        migrations.AlterField(
            model_name='bloqueioatendimentosaude',
            name='profissional',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='profissional_bloqueio_agendamento', to='rh.pessoafisica', verbose_name='Profissional'),
        ),
        migrations.AlterField(
            model_name='documentoprontuario',
            name='cadastrado_por',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='rh.pessoafisica'),
        ),
        migrations.AlterField(
            model_name='horarioatendimento',
            name='cadastrado_por',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='rh.pessoafisica'),
        ),
        migrations.AlterField(
            model_name='prontuario',
            name='pessoa_fisica',
            field=djtools.db.models.OneToOneFieldPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='rh.pessoafisica', verbose_name='Pessoa Física/Matrícula'),
        ),
        migrations.AlterField(
            model_name='registroadministrativo',
            name='profissional',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='rh.pessoafisica'),
        ),
    ]
