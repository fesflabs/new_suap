# Generated by Django 3.2.5 on 2023-03-24 12:20

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('ppe', '0047_auto_20230324_0954'),
    ]

    operations = [
        migrations.AlterField(
            model_name='perguntaavaliacao',
            name='tipo_resposta',
            field=djtools.db.models.CharFieldPlus(choices=[('Texto', 'Texto'), ('Texto de Avaliação', 'Texto de Avaliação'), ('Parágrafo', 'Parágrafo'), ('Número', 'Número'), ('Sim/Não', 'Sim/Não'), ('Sim/Não/NA', 'Sim/Não/NA'), ('Escala 0 a 5', 'Escala 0 a 5'), ('Escala 0 a 5 COMPETÊNCIA', 'Escala 0 a 5 COMPETÊNCIA'), ('Única Escolha', 'Única Escolha'), ('Múltipla Escolha', 'Múltipla Escolha')], max_length=100, verbose_name='Tipo de Resposta'),
        ),
    ]