# Generated by Django 2.2.24 on 2021-07-01 16:52

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('comum', '0020_emailblocklist'),
    ]

    operations = [
        migrations.AlterField(
            model_name='preferencia',
            name='tema',
            field=djtools.db.models.CharFieldPlus(choices=[('Padrão', 'Padrão'), ('Dunas', 'Dunas'), ('Aurora', 'Aurora'), ('Luna', 'Luna'), ('Gov.br', 'Gov.br'), ('Alto Contraste', 'Alto Contraste'), ('IFs', 'IFs')], default='Padrão', max_length=255, verbose_name='Opção de Tema'),
        ),
    ]