# Generated by Django 3.2.5 on 2023-01-31 13:44

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('residencia', '0032_alter_documentofrequenciamensalresidente_documento_fisico'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documentofrequenciamensalresidente',
            name='documento_fisico',
            field=djtools.db.models.FileFieldPlus(max_length=250, upload_to='residencia/frequencias_fisicas/'),
        ),
    ]