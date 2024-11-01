# Generated by Django 2.2.7 on 2019-11-18 16:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('calculos_pagamentos', '0002_auto_20191113_1644')]

    operations = [
        migrations.AlterField(
            model_name='periodocalculoprogressao',
            name='padrao_vencimento_novo',
            field=models.CharField(
                blank=True,
                choices=[
                    ['101', '101'],
                    ['102', '102'],
                    ['103', '103'],
                    ['104', '104'],
                    ['105', '105'],
                    ['106', '106'],
                    ['107', '107'],
                    ['108', '108'],
                    ['109', '109'],
                    ['110', '110'],
                    ['111', '111'],
                    ['112', '112'],
                    ['113', '113'],
                    ['114', '114'],
                    ['115', '115'],
                    ['116', '116'],
                    ['201', '201'],
                    ['202', '202'],
                    ['203', '203'],
                    ['204', '204'],
                    ['205', '205'],
                    ['206', '206'],
                    ['207', '207'],
                    ['208', '208'],
                    ['209', '209'],
                    ['210', '210'],
                    ['211', '211'],
                    ['212', '212'],
                    ['213', '213'],
                    ['214', '214'],
                    ['215', '215'],
                    ['216', '216'],
                    ['301', '301'],
                    ['302', '302'],
                    ['303', '303'],
                    ['304', '304'],
                    ['305', '305'],
                    ['306', '306'],
                    ['307', '307'],
                    ['308', '308'],
                    ['309', '309'],
                    ['310', '310'],
                    ['311', '311'],
                    ['312', '312'],
                    ['313', '313'],
                    ['314', '314'],
                    ['315', '315'],
                    ['316', '316'],
                    ['401', '401'],
                    ['402', '402'],
                    ['403', '403'],
                    ['404', '404'],
                    ['405', '405'],
                    ['406', '406'],
                    ['407', '407'],
                    ['408', '408'],
                    ['409', '409'],
                    ['410', '410'],
                    ['411', '411'],
                    ['412', '412'],
                    ['413', '413'],
                    ['414', '414'],
                    ['415', '415'],
                    ['416', '416'],
                ],
                max_length=3,
                null=True,
                verbose_name='Padrão de Vencimento Novo',
            ),
        ),
        migrations.AlterField(
            model_name='periodocalculoprogressao',
            name='padrao_vencimento_passado',
            field=models.CharField(
                blank=True,
                choices=[
                    ['101', '101'],
                    ['102', '102'],
                    ['103', '103'],
                    ['104', '104'],
                    ['105', '105'],
                    ['106', '106'],
                    ['107', '107'],
                    ['108', '108'],
                    ['109', '109'],
                    ['110', '110'],
                    ['111', '111'],
                    ['112', '112'],
                    ['113', '113'],
                    ['114', '114'],
                    ['115', '115'],
                    ['116', '116'],
                    ['201', '201'],
                    ['202', '202'],
                    ['203', '203'],
                    ['204', '204'],
                    ['205', '205'],
                    ['206', '206'],
                    ['207', '207'],
                    ['208', '208'],
                    ['209', '209'],
                    ['210', '210'],
                    ['211', '211'],
                    ['212', '212'],
                    ['213', '213'],
                    ['214', '214'],
                    ['215', '215'],
                    ['216', '216'],
                    ['301', '301'],
                    ['302', '302'],
                    ['303', '303'],
                    ['304', '304'],
                    ['305', '305'],
                    ['306', '306'],
                    ['307', '307'],
                    ['308', '308'],
                    ['309', '309'],
                    ['310', '310'],
                    ['311', '311'],
                    ['312', '312'],
                    ['313', '313'],
                    ['314', '314'],
                    ['315', '315'],
                    ['316', '316'],
                    ['401', '401'],
                    ['402', '402'],
                    ['403', '403'],
                    ['404', '404'],
                    ['405', '405'],
                    ['406', '406'],
                    ['407', '407'],
                    ['408', '408'],
                    ['409', '409'],
                    ['410', '410'],
                    ['411', '411'],
                    ['412', '412'],
                    ['413', '413'],
                    ['414', '414'],
                    ['415', '415'],
                    ['416', '416'],
                ],
                max_length=3,
                null=True,
                verbose_name='Padrão de Vencimento Anterior',
            ),
        ),
        migrations.AlterField(
            model_name='periodoinsalubridade',
            name='padrao_vencimento_novo',
            field=models.CharField(
                blank=True,
                choices=[
                    ['101', '101'],
                    ['102', '102'],
                    ['103', '103'],
                    ['104', '104'],
                    ['105', '105'],
                    ['106', '106'],
                    ['107', '107'],
                    ['108', '108'],
                    ['109', '109'],
                    ['110', '110'],
                    ['111', '111'],
                    ['112', '112'],
                    ['113', '113'],
                    ['114', '114'],
                    ['115', '115'],
                    ['116', '116'],
                    ['201', '201'],
                    ['202', '202'],
                    ['203', '203'],
                    ['204', '204'],
                    ['205', '205'],
                    ['206', '206'],
                    ['207', '207'],
                    ['208', '208'],
                    ['209', '209'],
                    ['210', '210'],
                    ['211', '211'],
                    ['212', '212'],
                    ['213', '213'],
                    ['214', '214'],
                    ['215', '215'],
                    ['216', '216'],
                    ['301', '301'],
                    ['302', '302'],
                    ['303', '303'],
                    ['304', '304'],
                    ['305', '305'],
                    ['306', '306'],
                    ['307', '307'],
                    ['308', '308'],
                    ['309', '309'],
                    ['310', '310'],
                    ['311', '311'],
                    ['312', '312'],
                    ['313', '313'],
                    ['314', '314'],
                    ['315', '315'],
                    ['316', '316'],
                    ['401', '401'],
                    ['402', '402'],
                    ['403', '403'],
                    ['404', '404'],
                    ['405', '405'],
                    ['406', '406'],
                    ['407', '407'],
                    ['408', '408'],
                    ['409', '409'],
                    ['410', '410'],
                    ['411', '411'],
                    ['412', '412'],
                    ['413', '413'],
                    ['414', '414'],
                    ['415', '415'],
                    ['416', '416'],
                ],
                max_length=3,
                null=True,
                verbose_name='Padrão de Vencimento',
            ),
        ),
        migrations.AlterField(
            model_name='periodoiq',
            name='padrao_vencimento_novo',
            field=models.CharField(
                choices=[
                    ['101', '101'],
                    ['102', '102'],
                    ['103', '103'],
                    ['104', '104'],
                    ['105', '105'],
                    ['106', '106'],
                    ['107', '107'],
                    ['108', '108'],
                    ['109', '109'],
                    ['110', '110'],
                    ['111', '111'],
                    ['112', '112'],
                    ['113', '113'],
                    ['114', '114'],
                    ['115', '115'],
                    ['116', '116'],
                    ['201', '201'],
                    ['202', '202'],
                    ['203', '203'],
                    ['204', '204'],
                    ['205', '205'],
                    ['206', '206'],
                    ['207', '207'],
                    ['208', '208'],
                    ['209', '209'],
                    ['210', '210'],
                    ['211', '211'],
                    ['212', '212'],
                    ['213', '213'],
                    ['214', '214'],
                    ['215', '215'],
                    ['216', '216'],
                    ['301', '301'],
                    ['302', '302'],
                    ['303', '303'],
                    ['304', '304'],
                    ['305', '305'],
                    ['306', '306'],
                    ['307', '307'],
                    ['308', '308'],
                    ['309', '309'],
                    ['310', '310'],
                    ['311', '311'],
                    ['312', '312'],
                    ['313', '313'],
                    ['314', '314'],
                    ['315', '315'],
                    ['316', '316'],
                    ['401', '401'],
                    ['402', '402'],
                    ['403', '403'],
                    ['404', '404'],
                    ['405', '405'],
                    ['406', '406'],
                    ['407', '407'],
                    ['408', '408'],
                    ['409', '409'],
                    ['410', '410'],
                    ['411', '411'],
                    ['412', '412'],
                    ['413', '413'],
                    ['414', '414'],
                    ['415', '415'],
                    ['416', '416'],
                ],
                max_length=3,
                verbose_name='Padrão de Vencimento',
            ),
        ),
        migrations.AlterField(
            model_name='periodomudancaregime',
            name='padrao_vencimento_novo',
            field=models.CharField(
                blank=True,
                choices=[
                    ['101', '101'],
                    ['102', '102'],
                    ['103', '103'],
                    ['104', '104'],
                    ['105', '105'],
                    ['106', '106'],
                    ['107', '107'],
                    ['108', '108'],
                    ['109', '109'],
                    ['110', '110'],
                    ['111', '111'],
                    ['112', '112'],
                    ['113', '113'],
                    ['114', '114'],
                    ['115', '115'],
                    ['116', '116'],
                    ['201', '201'],
                    ['202', '202'],
                    ['203', '203'],
                    ['204', '204'],
                    ['205', '205'],
                    ['206', '206'],
                    ['207', '207'],
                    ['208', '208'],
                    ['209', '209'],
                    ['210', '210'],
                    ['211', '211'],
                    ['212', '212'],
                    ['213', '213'],
                    ['214', '214'],
                    ['215', '215'],
                    ['216', '216'],
                    ['301', '301'],
                    ['302', '302'],
                    ['303', '303'],
                    ['304', '304'],
                    ['305', '305'],
                    ['306', '306'],
                    ['307', '307'],
                    ['308', '308'],
                    ['309', '309'],
                    ['310', '310'],
                    ['311', '311'],
                    ['312', '312'],
                    ['313', '313'],
                    ['314', '314'],
                    ['315', '315'],
                    ['316', '316'],
                    ['401', '401'],
                    ['402', '402'],
                    ['403', '403'],
                    ['404', '404'],
                    ['405', '405'],
                    ['406', '406'],
                    ['407', '407'],
                    ['408', '408'],
                    ['409', '409'],
                    ['410', '410'],
                    ['411', '411'],
                    ['412', '412'],
                    ['413', '413'],
                    ['414', '414'],
                    ['415', '415'],
                    ['416', '416'],
                ],
                max_length=3,
                null=True,
                verbose_name='Padrão de Vencimento',
            ),
        ),
        migrations.AlterField(
            model_name='periodopericulosidade',
            name='padrao_vencimento_novo',
            field=models.CharField(
                blank=True,
                choices=[
                    ['101', '101'],
                    ['102', '102'],
                    ['103', '103'],
                    ['104', '104'],
                    ['105', '105'],
                    ['106', '106'],
                    ['107', '107'],
                    ['108', '108'],
                    ['109', '109'],
                    ['110', '110'],
                    ['111', '111'],
                    ['112', '112'],
                    ['113', '113'],
                    ['114', '114'],
                    ['115', '115'],
                    ['116', '116'],
                    ['201', '201'],
                    ['202', '202'],
                    ['203', '203'],
                    ['204', '204'],
                    ['205', '205'],
                    ['206', '206'],
                    ['207', '207'],
                    ['208', '208'],
                    ['209', '209'],
                    ['210', '210'],
                    ['211', '211'],
                    ['212', '212'],
                    ['213', '213'],
                    ['214', '214'],
                    ['215', '215'],
                    ['216', '216'],
                    ['301', '301'],
                    ['302', '302'],
                    ['303', '303'],
                    ['304', '304'],
                    ['305', '305'],
                    ['306', '306'],
                    ['307', '307'],
                    ['308', '308'],
                    ['309', '309'],
                    ['310', '310'],
                    ['311', '311'],
                    ['312', '312'],
                    ['313', '313'],
                    ['314', '314'],
                    ['315', '315'],
                    ['316', '316'],
                    ['401', '401'],
                    ['402', '402'],
                    ['403', '403'],
                    ['404', '404'],
                    ['405', '405'],
                    ['406', '406'],
                    ['407', '407'],
                    ['408', '408'],
                    ['409', '409'],
                    ['410', '410'],
                    ['411', '411'],
                    ['412', '412'],
                    ['413', '413'],
                    ['414', '414'],
                    ['415', '415'],
                    ['416', '416'],
                ],
                max_length=3,
                null=True,
                verbose_name='Padrão de Vencimento',
            ),
        ),
        migrations.AlterField(
            model_name='periodotransporte',
            name='padrao_vencimento_novo',
            field=models.CharField(
                blank=True,
                choices=[
                    ['101', '101'],
                    ['102', '102'],
                    ['103', '103'],
                    ['104', '104'],
                    ['105', '105'],
                    ['106', '106'],
                    ['107', '107'],
                    ['108', '108'],
                    ['109', '109'],
                    ['110', '110'],
                    ['111', '111'],
                    ['112', '112'],
                    ['113', '113'],
                    ['114', '114'],
                    ['115', '115'],
                    ['116', '116'],
                    ['201', '201'],
                    ['202', '202'],
                    ['203', '203'],
                    ['204', '204'],
                    ['205', '205'],
                    ['206', '206'],
                    ['207', '207'],
                    ['208', '208'],
                    ['209', '209'],
                    ['210', '210'],
                    ['211', '211'],
                    ['212', '212'],
                    ['213', '213'],
                    ['214', '214'],
                    ['215', '215'],
                    ['216', '216'],
                    ['301', '301'],
                    ['302', '302'],
                    ['303', '303'],
                    ['304', '304'],
                    ['305', '305'],
                    ['306', '306'],
                    ['307', '307'],
                    ['308', '308'],
                    ['309', '309'],
                    ['310', '310'],
                    ['311', '311'],
                    ['312', '312'],
                    ['313', '313'],
                    ['314', '314'],
                    ['315', '315'],
                    ['316', '316'],
                    ['401', '401'],
                    ['402', '402'],
                    ['403', '403'],
                    ['404', '404'],
                    ['405', '405'],
                    ['406', '406'],
                    ['407', '407'],
                    ['408', '408'],
                    ['409', '409'],
                    ['410', '410'],
                    ['411', '411'],
                    ['412', '412'],
                    ['413', '413'],
                    ['414', '414'],
                    ['415', '415'],
                    ['416', '416'],
                ],
                max_length=3,
                null=True,
                verbose_name='Padrão de Vencimento',
            ),
        ),
    ]
