# Generated by Django 3.2.5 on 2022-12-09 10:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ppe', '0023_auto_20221209_0957'),
    ]

    operations = [
        migrations.AlterField(
            model_name='anamnese',
            name='chefe_parental',
            field=models.BooleanField(blank=True, choices=[(False, 'Não'), (True, 'Sim')], null=True, verbose_name='Você era chefa de família monoparental (sozinha)? (pergunta exclusiva para mulheres)'),
        ),
        migrations.RemoveField(
            model_name='anamnese',
            name='fez_cursos',
        ),
        migrations.AddField(
            model_name='anamnese',
            name='fez_cursos',
            field=models.ManyToManyField(to='ppe.CursosTrabalhadorEducando', verbose_name='Você fez ou faz algum desses cursos?'),
        ),
        migrations.AlterField(
            model_name='anamnese',
            name='fumante',
            field=models.BooleanField(choices=[(False, 'Não'), (True, 'Sim')], verbose_name='Fumo'),
        ),
        migrations.AlterField(
            model_name='anamnese',
            name='ingressou_faculdade',
            field=models.BooleanField(choices=[(False, 'Não'), (True, 'Sim')], verbose_name='Ingressou em algumafaculdade/universidade?'),
        ),
        migrations.RemoveField(
            model_name='anamnese',
            name='itens_residencia',
        ),
        migrations.AddField(
            model_name='anamnese',
            name='itens_residencia',
            field=models.ManyToManyField(to='ppe.ItensResidencia', verbose_name='Sua residência tem (*pode escolher mais de uma opção)'),
        ),
        migrations.RemoveField(
            model_name='anamnese',
            name='meio_transporte',
        ),
        migrations.AddField(
            model_name='anamnese',
            name='meio_transporte',
            field=models.ManyToManyField(to='ppe.MeioTransporte', verbose_name='Qual o meio de transporte utilizadoem seu deslocamento para o trabalho?'),
        ),
        migrations.RemoveField(
            model_name='anamnese',
            name='membros_familia_carteira_assinada',
        ),
        migrations.AddField(
            model_name='anamnese',
            name='membros_familia_carteira_assinada',
            field=models.ManyToManyField(to='ppe.MembrosCarteiraAssinada', verbose_name='Quais membros da sua família trabalham com carteira assinada?'),
        ),
        migrations.RemoveField(
            model_name='anamnese',
            name='onde_trabalhou_anteriormente',
        ),
        migrations.AddField(
            model_name='anamnese',
            name='onde_trabalhou_anteriormente',
            field=models.ManyToManyField(blank=True, null=True, to='ppe.TrabalhoAnteriorAoPPE', verbose_name='Caso você tenha trabalhado antes de ingressar no PPE, onde foi?'),
        ),
        migrations.RemoveField(
            model_name='anamnese',
            name='participa_grupos_sociais',
        ),
        migrations.AddField(
            model_name='anamnese',
            name='participa_grupos_sociais',
            field=models.ManyToManyField(to='ppe.ParticipacaoGruposSociais', verbose_name='Participação em grupos sociais (*pode escolher mais de uma opção)'),
        ),
        migrations.RemoveField(
            model_name='anamnese',
            name='participa_rede_social',
        ),
        migrations.AddField(
            model_name='anamnese',
            name='participa_rede_social',
            field=models.ManyToManyField(to='ppe.RedeSocial', verbose_name='Participa de alguma rede social?'),
        ),
        migrations.RemoveField(
            model_name='anamnese',
            name='reside_com',
        ),
        migrations.AddField(
            model_name='anamnese',
            name='reside_com',
            field=models.ManyToManyField(to='ppe.ResideCom', verbose_name='Reside com'),
        ),
        migrations.RemoveField(
            model_name='anamnese',
            name='residencia_saneamento_basico',
        ),
        migrations.AddField(
            model_name='anamnese',
            name='residencia_saneamento_basico',
            field=models.ManyToManyField(to='ppe.ResidenciaSaneamentoBasico', verbose_name='Sua residência tem (*pode escolher mais de uma opção)'),
        ),
        migrations.AlterField(
            model_name='anamnese',
            name='tentou_faculdade',
            field=models.BooleanField(choices=[(False, 'Não'), (True, 'Sim')], verbose_name='Tentou acesso à faculdade/universidade?'),
        ),
    ]