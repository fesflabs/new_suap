# Generated by Django 2.2.16 on 2020-09-15 14:30
import tqdm
from django.db import migrations


def get_or_create_vinculo(apps, dic, pessoa):
    Vinculo = apps.get_model('comum.Vinculo')
    PessoaExterna = apps.get_model('rh.PessoaExterna')
    ContentType = apps.get_model('contenttypes.ContentType')
    tipo_relacionamento_pessoaexterna = ContentType.objects.get(app_label='rh', model='pessoaexterna')
    tipo_relacionamento_pessoajuridica = ContentType.objects.get(app_label='rh', model='pessoajuridica')

    if pessoa.id in dic:
        vinculo_id = dic[pessoa.id]
    else:
        qs = PessoaExterna.objects.filter(cpf=pessoa.pessoafisica.documento_identificador, cpf__isnull=False) | PessoaExterna.objects.filter(
            username=pessoa.pessoafisica.username, username__isnull=False
        )
        if qs.exists():
            pe = qs[0]
            vinculo_id = Vinculo.objects.get(tipo_relacionamento=tipo_relacionamento_pessoaexterna, id_relacionamento=pe.id).id
            print(f'\n\nVínculo {vinculo_id} encontrado\n\n')
        elif hasattr(pessoa, 'pessoajuridica'):
            vinculo_id = Vinculo.objects.create(pessoa=pessoa, tipo_relacionamento=tipo_relacionamento_pessoajuridica, id_relacionamento=pessoa.id).id
            print(f'\n\nVínculo {vinculo_id} pj criado\n\n')
        else:
            pf_dict = pessoa.pessoafisica.__dict__.copy()
            pf_dict['matricula'] = pessoa.pessoafisica.documento_identificador
            pf_dict['pessoa_fisica_id'] = pessoa.id

            pf_dict.pop('_state')
            pf_dict.pop('id')
            pf_dict.pop('eh_aluno')
            pf_dict.pop('eh_prestador')
            pf_dict.pop('eh_servidor')
            pf_dict.pop('documento_identificador')
            pf_dict.pop('user_id')
            pf_dict.pop('search_fields_optimized')
            pf_dict.pop('pessoa_ptr_id')
            pe = PessoaExterna.objects.create(**pf_dict)
            vinculo_id = Vinculo.objects.create(pessoa=pessoa, tipo_relacionamento=tipo_relacionamento_pessoaexterna, id_relacionamento=pe.id).id
            print(f'\n\nVínculo {vinculo_id} criado pf\n\n')

    return vinculo_id


def atualizar_dados(apps, schema):
    ServicoEquipe = apps.get_model('catalogo_provedor_servico.ServicoEquipe')
    Solicitacao = apps.get_model('catalogo_provedor_servico.Solicitacao')
    SolicitacaoResponsavelHistorico = apps.get_model('catalogo_provedor_servico.SolicitacaoResponsavelHistorico')
    SolicitacaoHistoricoSituacao = apps.get_model('catalogo_provedor_servico.SolicitacaoHistoricoSituacao')
    PessoaFisica = apps.get_model('rh.PessoaFisica')
    Vinculo = apps.get_model('comum.Vinculo')

    vinculos = Vinculo.objects.all()
    dic = {}
    for vinculo in vinculos:
        dic[vinculo.pessoa_id] = vinculo.pk

    print('\nAtualizando Serviço Equipe\n')
    for pessoa in tqdm.tqdm(PessoaFisica.objects.filter(servicoequipe__isnull=False).only('id').distinct()):
        ServicoEquipe.objects.filter(pessoa_fisica=pessoa).update(vinculo=get_or_create_vinculo(apps, dic, pessoa))

    print('\nAtualizando Atribuinte da Solicitação\n')
    for pessoa in tqdm.tqdm(PessoaFisica.objects.filter(solicitacao_atribuinte__isnull=False).only('id').distinct()):
        Solicitacao.objects.filter(atribuinte=pessoa).update(vinculo_atribuinte=get_or_create_vinculo(apps, dic, pessoa))

    print('\nAtualizando Responsável da Solicitação\n')
    for pessoa in tqdm.tqdm(PessoaFisica.objects.filter(solicitacao__isnull=False).only('id').distinct()):
        Solicitacao.objects.filter(responsavel=pessoa).update(vinculo_responsavel=get_or_create_vinculo(apps, dic, pessoa))

    print('\nAtualizando Atribuinte da SolicitacaoResponsavelHistorico\n')
    for pessoa in tqdm.tqdm(PessoaFisica.objects.filter(solicitacao_historico_atribuinte__isnull=False).only('id').distinct()):
        SolicitacaoResponsavelHistorico.objects.filter(atribuinte=pessoa).update(vinculo_atribuinte=get_or_create_vinculo(apps, dic, pessoa))

    print('\nAtualizando Responsável da SolicitacaoResponsavelHistorico\n')
    for pessoa in tqdm.tqdm(PessoaFisica.objects.filter(solicitacaoresponsavelhistorico__isnull=False).only('id').distinct()):
        SolicitacaoResponsavelHistorico.objects.filter(responsavel=pessoa).update(vinculo_responsavel=get_or_create_vinculo(apps, dic, pessoa))

    print('\nAtualizando Responsável da SolicitacaoHistoricoSituacao\n')
    for pessoa in tqdm.tqdm(PessoaFisica.objects.filter(solicitacaoresponsavelhistorico__isnull=False).only('id').distinct()):
        SolicitacaoHistoricoSituacao.objects.filter(responsavel=pessoa).update(vinculo_responsavel=get_or_create_vinculo(apps, dic, pessoa))


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo_provedor_servico', '0037_pessoa_unica_01'),
    ]

    operations = [
        migrations.RunPython(atualizar_dados)
    ]