# Generated by Django 3.2.5 on 2022-07-01 13:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0038_auto_20220610_0752'),
    ]

    operations = [
        migrations.AlterField(
            model_name='papel',
            name='tipo_papel',
            field=models.CharField(choices=[('cargo', 'cargo'), ('funcao', 'funcao'), ('comissaoconselho', 'comissaoconselho'), ('ocupacao', 'ocupacao'), ('discente', 'discente'), ('usuarioexterno', 'usuarioexterno')], default='cargo', max_length=255, verbose_name='Tipo de papel'),
        ),
    ]