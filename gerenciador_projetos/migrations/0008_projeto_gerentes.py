# Generated by Django 3.2.5 on 2022-03-14 15:03

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('gerenciador_projetos', '0007_alter_historicoevolucao_data_conclusao'),
    ]

    operations = [
        migrations.AddField(
            model_name='projeto',
            name='gerentes',
            field=models.ManyToManyField(related_name='gerenciador_projeto_gerentes_set', to=settings.AUTH_USER_MODEL, verbose_name='Gerentes'),
        ),
    ]