# Generated by Django 3.2.5 on 2022-04-05 21:29

from django.db import migrations
import djtools.unaccent_field


class Migration(migrations.Migration):

    dependencies = [
        ('protocolo', '0002_alter_processo_interessado_nome'),
    ]

    operations = [
        migrations.AlterField(
            model_name='processo',
            name='interessado_nome',
            field=djtools.unaccent_field.UnaccentField(max_length=200, verbose_name='Nome do Interessado'),
        ),
    ]