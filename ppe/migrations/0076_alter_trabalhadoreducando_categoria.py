# Generated by Django 3.2.5 on 2023-07-25 11:27

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('ppe', '0075_auto_20230725_1058'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trabalhadoreducando',
            name='categoria',
            field=djtools.db.models.CharFieldPlus(blank=True, choices=[['Biomedicina', 'Biomedicina'], ['Enfermagem', 'Enfermagem'], ['Farmácia', 'Farmácia'], ['Fisioterapia', 'Fisioterapia'], ['Fonoaudiologia', 'Fonoaudiologia'], ['Medicina', 'Medicina'], ['Medicina Veterinária', 'Medicina Veterinária'], ['Nutrição', 'Nutrição'], ['Odontologia', 'Odontologia'], ['Psicologia', 'Psicologia'], ['Terapia Ocupacional', 'Terapia Ocupacional'], ['Saúde Ocupacional', 'Saúde Ocupacional'], ['TÉCNICO EM ADMINISTRAÇÃO', 'TÉCNICO EM ADMINISTRAÇÃO'], ['TÉCNICO EM ANÁLISES CLÍNICAS', 'TÉCNICO EM ANÁLISES CLÍNICAS'], ['TÉCNICO EM COMÉRCIO', 'TÉCNICO EM COMÉRCIO'], ['TÉCNICO EM COMUNICAÇÃO VISUAL', 'TÉCNICO EM COMUNICAÇÃO VISUAL'], ['TÉCNICO EM CONTABILIDADE', 'TÉCNICO EM CONTABILIDADE'], ['TÉCNICO EM ENFERMAGEM', 'TÉCNICO EM ENFERMAGEM'], ['TÉCNICO EM FARMÁCIA', 'TÉCNICO EM FARMÁCIA'], ['TÉCNICO EM FINANÇAS', 'TÉCNICO EM FINANÇAS'], ['TÉCNICO EM GERÊNCIA EM SAÚDE', 'TÉCNICO EM GERÊNCIA EM SAÚDE'], ['TÉCNICO EM INFORMÁTICA', 'TÉCNICO EM INFORMÁTICA'], ['TÉCNICO EM LOGÍSTICA', 'TÉCNICO EM LOGÍSTICA'], ['TÉCNICO EM MANUTENÇÃO E SUPORTE EM INFORMÁTICA', 'TÉCNICO EM MANUTENÇÃO E SUPORTE EM INFORMÁTICA'], ['TÉCNICO EM MEIO AMBIENTE', 'TÉCNICO EM MEIO AMBIENTE'], ['TÉCNICO EM NUTRIÇÃO E DIETÉTICA', 'TÉCNICO EM NUTRIÇÃO E DIETÉTICA'], ['TÉCNICO EM RECURSOS HUMANOS', 'TÉCNICO EM RECURSOS HUMANOS'], ['TÉCNICO EM REDES DE COMPUTADORES', 'TÉCNICO EM REDES DE COMPUTADORES'], ['TÉCNICO EM SAÚDE BUCAL', 'TÉCNICO EM SAÚDE BUCAL'], ['TÉCNICO EM SECRETARIADO', 'TÉCNICO EM SECRETARIADO'], ['TÉCNICO EM SEGURANÇA DO TRABALHO', 'TÉCNICO EM SEGURANÇA DO TRABALHO'], ['TÉCNICO EM VENDAS', 'TÉCNICO EM VENDAS']], max_length=100, null=True, verbose_name='Categoria'),
        ),
    ]