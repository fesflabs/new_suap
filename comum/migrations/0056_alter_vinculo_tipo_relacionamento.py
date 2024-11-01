# Generated by Django 3.2.5 on 2023-03-30 16:20

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('comum', '0055_alter_vinculo_tipo_relacionamento'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vinculo',
            name='tipo_relacionamento',
            field=djtools.db.models.ForeignKeyPlus(limit_choices_to=models.Q(models.Q(('app_label', 'rh'), ('model', 'servidor')), models.Q(('app_label', 'comum'), ('model', 'prestadorservico')), models.Q(('app_label', 'edu'), ('model', 'aluno')), models.Q(('app_label', 'rh'), ('model', 'pessoajuridica')), models.Q(('app_label', 'rh'), ('model', 'pessoaexterna')), models.Q(('app_label', 'residencia'), ('model', 'residente')), models.Q(('app_label', 'ppe'), ('model', 'chefiappe')), _connector='OR'), on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype', verbose_name='Tipo de Relacionamento'),
        ),
    ]
