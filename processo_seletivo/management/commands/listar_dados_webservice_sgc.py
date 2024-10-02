# -*- coding: utf-8 -*-

import datetime
import urllib.request
import urllib.error
import urllib.parse
from xml.dom import minidom
import json

from djtools.management.commands import BaseCommandPlus
from processo_seletivo.models import WebService
from rh.models import UnidadeOrganizacional


class Command(BaseCommandPlus):
    def handle(self, *args, **options):

        # Filtro
        filtro_webservice_id = 2
        filtro_ano = 2016

        title = 'Editais - Análise de Dados do SGC'
        print('')
        print(('-' * len(title)))
        print(title)
        print(('Webservice: %d' % filtro_webservice_id))
        print(('Ano: %d' % filtro_ano))
        print(('-' * len(title)))
        print(('Início do processamento: %s' % datetime.datetime.now().strftime('%d/%m/%Y - %H:%M:%S')))
        print()

        qs_ws = WebService.objects.filter(id=filtro_webservice_id)
        for ws in qs_ws:
            print(('Carregando editais do webserives %s .' % ws))

            xml = None
            try:
                print()
                print(('Tentando consumir o webservice "%s"' % ws.url_editais))
                xml = urllib.request.urlopen(ws.url_editais).read()
                print('Webservice carregado com sucesso.')
            except Exception as e:
                print(('Erro ao consumir o webservices. Detalhes: %s' % e))
                return

            qtd_vagas_total = 0
            qtd_inscricoes_total = 0
            qtd_inscricoes_confirmadas_total = 0

            doc = minidom.parseString(xml)

            print(('-' * 200))
            print('Edital;Código;Ano;Semestre;Sisu;Remanescentes;Vagas;Inscrições;Inscrições Deferidas')
            for edital_xml in doc.getElementsByTagName('edital'):
                ano = int(edital_xml.getElementsByTagName('ano')[0].firstChild.nodeValue)
                if ano == filtro_ano:
                    codigo = edital_xml.getElementsByTagName('codigo')[0].firstChild.nodeValue
                    semestre = edital_xml.getElementsByTagName('semestre')[0].firstChild.nodeValue
                    remanescentes = edital_xml.getElementsByTagName('remanescentes')[0].firstChild.nodeValue == 'Sim'

                    sisu = edital_xml.getElementsByTagName('sisu')[0].firstChild.nodeValue == 'Sim'
                    qtd_vagas = int(edital_xml.getElementsByTagName('qtd_vagas')[0].firstChild.nodeValue or 0)
                    qtd_inscricoes = int(edital_xml.getElementsByTagName('qtd_inscricoes')[0].firstChild.nodeValue or 0)
                    qtd_inscricoes_confirmadas = int(edital_xml.getElementsByTagName('qtd_inscricoes_confirmadas')[0].firstChild.nodeValue or 0)

                    detalhamento_por_campus = edital_xml.getElementsByTagName('detalhamento_por_campus')[0].firstChild.nodeValue

                    if edital_xml.getElementsByTagName('descricao')[0].firstChild:
                        descricao = '%s de %s/%s' % (edital_xml.getElementsByTagName('descricao')[0].firstChild.nodeValue, ano, semestre)
                    else:
                        descricao = 'Edital %s de %s/%s' % (codigo, ano, semestre)

                    qtd_vagas_total += int(qtd_vagas)
                    qtd_inscricoes_total += int(qtd_inscricoes)
                    qtd_inscricoes_confirmadas_total += int(qtd_inscricoes_confirmadas)

                    print(('%s;%s;%s;%s;%s;%s;%d;%d;%d' % (descricao, codigo, ano, semestre, sisu, remanescentes, qtd_vagas, qtd_inscricoes, qtd_inscricoes_confirmadas)))
                    editais_sgc_dict_list = json.loads(detalhamento_por_campus)
                    for edital in editais_sgc_dict_list:
                        campus = UnidadeOrganizacional.objects.suap().get(pk=edital['suap_unidade_organizacional_id'])
                        print(
                            (
                                '   Campus SGC: %s  /  Campus SUAP: %s  /  Vagas: %s  /  Inscricões: %s  /  Inscrições Confirmadas: %s'
                                % (edital['campus'], campus, edital['qtd_vagas'], edital['qtd_inscricoes'], edital['qtd_inscricoes_confirmadas'])
                            )
                        )

            print(('-' * 200))
            print(
                (
                    'Total de Inscritos Deferidos(I);%d;Total de Vagas(VO);%d;Índice;%.4f'
                    % (qtd_inscricoes_confirmadas_total, qtd_vagas_total, float(qtd_inscricoes_confirmadas_total) / qtd_vagas_total)
                )
            )
            print(('Total de Inscritos;%d;Total de Vagas;%d;Índice;%.4f' % (qtd_inscricoes_total, qtd_vagas_total, float(qtd_inscricoes_total) / qtd_vagas_total)))

        print()
        print('Processamento concluído com sucesso')
        print(('Fim do processamento: %s' % datetime.datetime.now().strftime('%d/%m/%Y - %H:%M:%S')))
