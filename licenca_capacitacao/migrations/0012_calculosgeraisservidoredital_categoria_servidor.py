# Generated by Django 2.2.16 on 2021-05-18 20:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('licenca_capacitacao', '0011_auto_20210518_1731'),
    ]

    operations = [
        migrations.AddField(
            model_name='calculosgeraisservidoredital',
            name='categoria_servidor',
            field=models.CharField(choices=[['docente', 'Docente'], ['tecnico_administrativo', 'Técnico-Administrativo']], default='tecnico_administrativo', max_length=30),
        ),
    ]
