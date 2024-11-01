# Generated by Django 2.2.5 on 2019-10-09 15:09

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [('comum', '0003_auto_20191002_1113')]

    operations = [
        migrations.AlterField(model_name='user', name='last_name', field=models.CharField(blank=True, max_length=150, verbose_name='last name')),
        migrations.AlterField(
            model_name='vinculo',
            name='tipo_relacionamento',
            field=djtools.db.models.ForeignKeyPlus(
                limit_choices_to=models.Q(
                    models.Q(('app_label', 'rh'), ('model', 'servidor')),
                    models.Q(('app_label', 'comum'), ('model', 'prestadorservico')),
                    models.Q(('app_label', 'edu'), ('model', 'aluno')),
                    models.Q(('app_label', 'rh'), ('model', 'pessoajuridica')),
                    models.Q(('app_label', 'rh'), ('model', 'pessoaexterna')),
                    _connector='OR',
                ),
                on_delete=django.db.models.deletion.CASCADE,
                to='contenttypes.ContentType',
                verbose_name='Tipo de Relacionamento',
            ),
        ),
    ]
