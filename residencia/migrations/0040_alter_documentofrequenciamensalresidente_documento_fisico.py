# Generated by Django 3.2.5 on 2023-02-02 11:22

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('residencia', '0039_merge_20230202_1048'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documentofrequenciamensalresidente',
            name='documento_fisico',
            field=djtools.db.models.FileFieldPlus(blank=True, max_length=250, null=True, upload_to='residencia/frequencias_fisicas/'),
        ),
    ]
