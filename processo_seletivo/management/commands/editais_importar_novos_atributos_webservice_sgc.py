# -*- coding: utf-8 -*-

import urllib.request
import urllib.error
import urllib.parse
from xml.dom import minidom

from djtools.management.commands import BaseCommandPlus
from processo_seletivo.models import Edital, WebService
import datetime
import json


class Command(BaseCommandPlus):
    def handle(self, *args, **options):

        title = 'Editais - Importação de Novos Atributos Vindos Do SGC'
        print('')
        print(('- ' * len(title)))
        print(title)
        print(('- ' * len(title)))
        print(('Início do processamento: %s' % datetime.datetime.now().strftime('%d/%m/%Y - %H:%M:%S')))
        print()

        qs_ws = WebService.objects.filter(id=2)
        for ws in qs_ws:
            print(('Carregando editais do webserives %s .' % ws))
            print('Obs: Apenas os editais já cadastrados no banco de dados do SUAP terão os dados básicos atualizados.')

            xml = None
            try:
                print()
                print(('Tentando consumir o webservice "%s"' % ws.url_editais))
                xml = urllib.request.urlopen(ws.url_editais).read()
                print('Webservice carregado com sucesso.')
            except Exception as e:
                print(('Erro ao consumir o webservices. Detalhes: %s' % e))
                return

            doc = minidom.parseString(xml)
            for edital_xml in doc.getElementsByTagName('edital'):
                codigo = edital_xml.getElementsByTagName('codigo')[0].firstChild.nodeValue
                ano = edital_xml.getElementsByTagName('ano')[0].firstChild.nodeValue
                semestre = edital_xml.getElementsByTagName('semestre')[0].firstChild.nodeValue
                remanescentes = edital_xml.getElementsByTagName('remanescentes')[0].firstChild.nodeValue == 'Sim'

                sisu = edital_xml.getElementsByTagName('sisu')[0].firstChild.nodeValue == 'Sim'
                qtd_vagas = edital_xml.getElementsByTagName('qtd_vagas')[0].firstChild.nodeValue
                qtd_inscricoes = edital_xml.getElementsByTagName('qtd_inscricoes')[0].firstChild.nodeValue
                qtd_inscricoes_confirmadas = edital_xml.getElementsByTagName('qtd_inscricoes_confirmadas')[0].firstChild.nodeValue
                detalhamento_por_campus = edital_xml.getElementsByTagName('detalhamento_por_campus')[0].firstChild.nodeValue

                if edital_xml.getElementsByTagName('descricao')[0].firstChild:
                    descricao = '%s de %s/%s' % (edital_xml.getElementsByTagName('descricao')[0].firstChild.nodeValue, ano, semestre)
                else:
                    descricao = 'Edital %s de %s/%s' % (codigo, ano, semestre)

                print()
                print(('%s - Código %s - Ano %s - Semestre: %s - Sisu: %s' % (descricao, codigo, ano, semestre, sisu)))
                try:
                    edital = Edital.objects.get(codigo=codigo, webservice=ws)
                except Edital.DoesNotExist:
                    edital = None

                if edital:
                    # edital.codigo = edital_selecionado_webservice.codigo
                    # edital.descricao = edital_selecionado_webservice.descricao
                    # edital.ano = edital_selecionado_webservice.ano
                    # edital.semestre = edital_selecionado_webservice.semestre

                    edital.sisu = sisu
                    edital.qtd_vagas = qtd_vagas
                    edital.qtd_inscricoes = qtd_inscricoes
                    edital.qtd_inscricoes_confirmadas = qtd_inscricoes_confirmadas
                    edital.detalhamento_por_campus = detalhamento_por_campus

                    edital.remanescentes = remanescentes
                    # edital.webservice = edital_selecionado_webservice.webservice

                    edital.save()

                    editais_sgc_dict_list = json.loads(edital.detalhamento_por_campus)
                    for edital in editais_sgc_dict_list:
                        print(
                            (
                                'Campus SGC: %s  /  Suap_Uo_Id: %s  /  Vagas: %s  /  Inscricões: %s  /  Inscrições Confirmadas: %s'
                                % (edital['campus'], edital['suap_unidade_organizacional_id'], edital['qtd_vagas'], edital['qtd_inscricoes'], edital['qtd_inscricoes_confirmadas'])
                            )
                        )

                    print('Edital cadastrado no SUAP. Dados atualizados com sucesso.')
                else:
                    print('Edital não cadastrado no SUAP.')

        print()
        print('Processamento concluído com sucesso')
        print(('Fim do processamento: %s' % datetime.datetime.now().strftime('%d/%m/%Y - %H:%M:%S')))
