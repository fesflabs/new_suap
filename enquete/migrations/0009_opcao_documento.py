# Generated by Django 3.2.5 on 2022-07-15 10:52

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('enquete', '0008_alter_enquete_manter_enquete_inicio'),
    ]

    operations = [
        migrations.AddField(
            model_name='opcao',
            name='documento',
            field=djtools.db.models.FileFieldPlus(blank=True, upload_to='enquete/opcao/documento'),
        ),
    ]