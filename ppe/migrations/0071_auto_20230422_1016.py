# Generated by Django 3.2.5 on 2023-04-22 10:16

from django.db import migrations, models
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('ppe', '0070_alter_chefiasetorhistorico_unique_together'),
    ]

    operations = [
        migrations.AddField(
            model_name='cursoturma',
            name='integracao_com_moodle',
            field=models.BooleanField(default=False, verbose_name='Integração com o Moodle'),
        ),
        migrations.AddField(
            model_name='cursoturma',
            name='nome_breve_curso_moodle',
            field=djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Nome breve do curso'),
        ),
        migrations.AddField(
            model_name='cursoturma',
            name='url_moodle',
            field=djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='URL do Moodle'),
        ),
    ]
