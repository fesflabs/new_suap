# Generated by Django 2.2.10 on 2020-04-02 11:32

from django.db import migrations
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [('eventos', '0005_auto_20200306_0932')]

    operations = [
        migrations.AlterField(
            model_name='evento',
            name='campus',
            field=djtools.db.models.ForeignKeyPlus(
                on_delete=django.db.models.deletion.CASCADE, related_name='campus_responsavel', to='rh.UnidadeOrganizacional', verbose_name='Campus do Coordenador'
            ),
        ),
        migrations.AlterField(
            model_name='evento',
            name='setor',
            field=djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='rh.Setor', verbose_name='Setor do Coordenador'),
        ),
    ]
