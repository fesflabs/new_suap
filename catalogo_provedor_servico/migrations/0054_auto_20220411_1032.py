# Generated by Django 3.2.5 on 2022-04-11 10:32
import tqdm
import json

from django.db import migrations


def atualizar_dados_telefone(apps, schema):
    SolicitacaoEtapa = apps.get_model('catalogo_provedor_servico.SolicitacaoEtapa')
    Aluno = apps.get_model('edu.Aluno')

    for solicitacao_etapa in tqdm.tqdm(SolicitacaoEtapa.objects.filter(numero_etapa=2, solicitacao__status='ATENDIDO')):
        formulario = json.loads(solicitacao_etapa.dados).get('formulario')
        if formulario:
            for field_govbr in formulario:
                if field_govbr.get('name') == 'telefone_govbr' and field_govbr.get('value'):
                    for field_principal in formulario:
                        if field_principal.get('name') == 'telefone_principal' and not field_principal.get('value'):
                            if solicitacao_etapa.solicitacao.status_detalhamento.startswith('Matrícula <a href="/edu/aluno/'):
                                matricula = solicitacao_etapa.solicitacao.status_detalhamento[30:].split('"')[0]
                            else:
                                matricula = solicitacao_etapa.solicitacao.status_detalhamento.split()[1]
                            aluno = Aluno.objects.filter(matricula=matricula).first()
                            if aluno and not aluno.telefone_principal:
                                aluno.telefone_principal = field_govbr.get('value')
                                aluno.save()


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo_provedor_servico', '0053_auto_20211122_1708'),
    ]

    operations = [
        migrations.RunPython(atualizar_dados_telefone)
    ]