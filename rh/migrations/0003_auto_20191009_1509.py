# Generated by Django 2.2.5 on 2019-10-09 15:09

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [('rh', '0002_auto_20190902_1545')]

    operations = [
        migrations.AlterField(
            model_name='papel',
            name='papel_content_type',
            field=djtools.db.models.ForeignKeyPlus(
                limit_choices_to=models.Q(
                    models.Q(('app_label', 'rh'), ('model', 'CargoEmprego')),
                    models.Q(('app_label', 'rh'), ('model', 'Funcao')),
                    models.Q(('app_label', 'comum'), ('model', 'Ocupacao')),
                    _connector='OR',
                ),
                on_delete=django.db.models.deletion.CASCADE,
                to='contenttypes.ContentType',
                verbose_name='Papel (Type)',
            ),
        ),
        migrations.AlterField(
            model_name='unidadeorganizacional',
            name='equivalente',
            field=djtools.db.models.ForeignKeyPlus(
                blank=True,
                help_text='Campus SUAP equivalente. Preencha caso esteja editando um campus SIAPE.',
                limit_choices_to={'setor__codigo__isnull': True},
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='rh.UnidadeOrganizacional',
            ),
        ),
    ]