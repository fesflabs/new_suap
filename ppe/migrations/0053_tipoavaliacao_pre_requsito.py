# Generated by Django 3.2.5 on 2023-03-25 09:35

from django.db import migrations
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('ppe', '0052_auto_20230325_0915'),
    ]

    operations = [
        migrations.AddField(
            model_name='tipoavaliacao',
            name='pre_requsito',
            field=djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='ppe.tipoavaliacao', verbose_name='Pré requsito'),
        ),
    ]
