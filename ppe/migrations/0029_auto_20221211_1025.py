# Generated by Django 3.2.5 on 2022-12-11 10:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ppe', '0028_alter_anamnese_ano_ingresso_ppe'),
    ]

    operations = [
        migrations.AlterField(
            model_name='anamnese',
            name='link_facebook',
            field=models.URLField(blank=True, null=True, verbose_name='Link da sua conta no Facebook'),
        ),
        migrations.AlterField(
            model_name='anamnese',
            name='link_instagram',
            field=models.URLField(blank=True, null=True, verbose_name='Link da sua conta no Instagram'),
        ),
        migrations.AlterField(
            model_name='anamnese',
            name='outra_rede_social',
            field=models.URLField(blank=True, null=True, verbose_name='Link da sua conta em outras redes sociais (se tiver)'),
        ),
    ]