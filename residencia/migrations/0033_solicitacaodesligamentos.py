# Generated by Django 3.2.5 on 2023-01-31 11:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('residencia', '0032_solicitacaousuario'),
    ]

    operations = [
        migrations.CreateModel(
            name='SolicitacaoDesligamentos',
            fields=[
                ('solicitacaousuario_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='residencia.solicitacaousuario')),
                ('motivo', models.TextField(null=True, verbose_name='Motivo')),
            ],
            options={
                'verbose_name': 'Solicitação de Desligamentos',
                'verbose_name_plural': 'Solicitações de Desligamentos',
            },
            bases=('residencia.solicitacaousuario',),
        ),
    ]
