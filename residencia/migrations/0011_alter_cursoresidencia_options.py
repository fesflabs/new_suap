# Generated by Django 3.2.5 on 2022-10-26 20:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('residencia', '0010_alter_componente_ch_hora_aula'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='cursoresidencia',
            options={'ordering': ('-ativo',), 'verbose_name': 'Curso Residênca', 'verbose_name_plural': 'Cursos Residêncas'},
        ),
    ]
