import requests
from django.core.management.base import BaseCommand

from catalogo_provedor_servico.models import Servico
from comum.models import Configuracao


# O parâmetro "codigoUnidade" é o código siorg. No caso do IFRN o código é o 439.
# https://siorg.planejamento.gov.br/siorg-cidadao-webapp/pages/listar_orgaos_estruturas/listar_orgaos_estruturas.jsf
# http://estruturaorganizacional.dados.gov.br/doc/orgao-entidade.xml
# http://estruturaorganizacional.dados.gov.br/doc/unidade-organizacional/439
# https://www.governoeletronico.gov.br/eixos-de-atuacao/governo/novo-siorg/documentos-e-arquivos/SIORG-NovoSiorg-v1.1-WebServices.pdf

# Exemplo de chamada:
# python manage.py importar_servicos_govbr


class Command(BaseCommand):
    def handle(self, *args, **options):
        instituicao_codigo_siorg = Configuracao.get_valor_por_chave('comum', 'instituicao_codigo_siorg')
        url_servicos_gov_br = Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'url_servicos_gov_br')

        if not instituicao_codigo_siorg:
            raise Exception('O parâmetro "instituicao_codigo_siorg" não foi encontrado. Defina-o em http://dominio.do.suap/comum/configuracao/ e rode este comando novamente.')

        if not url_servicos_gov_br:
            raise Exception('O parâmetro "url_servicos_gov_br" não foi encontrado. Defina-o em http://dominio.do.suap/comum/configuracao/ e rode este comando novamente.')

        url = '{}/{}'.format(url_servicos_gov_br, instituicao_codigo_siorg)
        servicos_portal = requests.get(url).json()
        for servico_portal in servicos_portal['resposta']:
            id_servico_portal_govbr = servico_portal['id'].split('/')[-1]
            titulo = servico_portal['nome']
            descricao = servico_portal['descricao']

            servico = Servico.objects.filter(id_servico_portal_govbr=id_servico_portal_govbr)
            if servico.exists():
                servico.update(titulo=titulo, descricao=descricao)
                # servico.update(titulo=titulo, descricao=descricao, icone='fa fa-question-circle')
                print('Serviço "{} - {}" atualizado com sucesso.'.format(id_servico_portal_govbr, titulo))
            else:
                Servico.objects.create(id_servico_portal_govbr=id_servico_portal_govbr, icone='fa fa-question-circle', titulo=titulo, descricao=descricao, ativo=False)
                print('Serviço "{} - {}" inserido com sucesso.'.format(id_servico_portal_govbr, titulo))
