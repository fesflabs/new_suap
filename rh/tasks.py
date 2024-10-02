import os
import tempfile
import zipfile

from django.conf import settings
from django.db.models import Q

from djtools.assincrono import task
from djtools.choices import campos
from djtools.html.graficos import PieChart
from djtools.storages import cache_file
from djtools.utils import CsvResponse, XlsResponse, group_by, render_html_file


def _get_alias_campo(campo):
    # Recupera o alias do campo para formato legível
    for dicionario in campos:
        if dicionario['campo'] == campo:
            return str(dicionario['alias'])
        elif campo == 'nome':
            return 'Nome'
        elif campo == 'matricula':
            return 'Matrícula'


def get_miniaturas(servidores_qs):
    """
    Retorna False caso haja servidores sem fotos no resultado da busca
    """
    servidores = servidores_qs.exclude(Q(foto__isnull=True) | Q(foto=''))
    miniaturas = []
    for s in servidores:
        try:
            remote_filename = s.foto.name.replace('fotos/', 'fotos/150x200/')
            local_filename = cache_file(remote_filename)
            if os.path.exists(local_filename):
                miniaturas.append((local_filename, f'{s.matricula}.jpg'))
        except Exception:
            pass
    return miniaturas


def get_fotos_zip(servidores):
    """
    Cria o arquivo zip de fotos de servidores
    """
    response = tempfile.NamedTemporaryFile(mode='w+b', dir=settings.TEMP_DIR, delete=False, suffix='.zip')
    response.close()
    zip_file = zipfile.ZipFile(response.name, 'w', zipfile.ZIP_DEFLATED)

    miniaturas = get_miniaturas(servidores)

    for m in miniaturas:
        zip_file.write(*m)
    zip_file.close()
    return response.name


def gerar_xls_busca_servidor(request, task, servidores_qs, campos_selecionados):
    rows = []
    header = []
    if request.GET.get('format') == 'csv':
        header = ["#", "MATRICULA", "SERVIDOR"]
    elif request.GET.get('format') == 'xls':
        header = ["MATRICULA", "SERVIDOR"]
    for campo in campos_selecionados:
        if campo == 'endereco':
            header.append('LOGRADOURO')
            header.append('NUMERO')
            header.append('COMPLEMENTO')
            header.append('BAIRRO')
            header.append('MUNICIPIO')
            header.append('CEP')
        header.append(str(campo).upper().replace('_', ' '))
    rows.append(header)
    idx = 0
    for servidor in task.iterate(servidores_qs):
        row = []
        if request.GET.get('format') == 'csv':
            row = [idx + 1, servidor.matricula, servidor.nome]
        elif request.GET.get('format') == 'xls':
            row = [servidor.matricula, servidor.nome]
        for campo in campos_selecionados:
            if campo == 'endereco':
                row.append(servidor.endereco_logradouro)
                row.append(servidor.endereco_numero)
                row.append(servidor.endereco_complemento)
                row.append(servidor.endereco_bairro)
                row.append(servidor.endereco_municipio)
                row.append(servidor.endereco_cep)
            if callable(getattr(servidor, campo)):
                row.append(getattr(servidor, campo)())
            else:
                row.append(getattr(servidor, campo))
        idx += 1
        rows.append(row)
    # Formato CSV
    if request.GET.get('format') == 'csv':
        return CsvResponse(rows, processo=task)
    # Formato XLS
    elif request.GET.get('format') == 'xls':
        return XlsResponse(rows, processo=task)


@task('Gerar Busca de Servidor')
def gerar_busca_servidor(request, cleaned_data, servidores_qs, campos_selecionados, encoded_url, task=None):
    task.update_progress(1)
    url_base = '/rh/servidor/buscar/' + '?' + encoded_url
    url_csv = url_base + '&format=csv'
    url_xls = url_base + '&format=xls'
    url_zip = ''
    tem_fotos = servidores_qs.exclude(Q(foto__isnull=True) | Q(foto='')).exists()
    # Só poderá haver formato zip caso algum servidor retornado pela busca tenha foto
    if tem_fotos:
        url_zip = url_base + '&format=zip'

    if request.GET.get('format') == 'zip':
        return task.finalize('Arquivo de fotos gerado com sucesso.', '..', file_path=get_fotos_zip(servidores_qs))

    if request.GET.get('format') in ['csv', 'xls']:
        return gerar_xls_busca_servidor(request, task, servidores_qs, campos_selecionados)

    # Populando lista de dicionário de servidores
    servidores_dict = []
    agrupador_valores = dict()
    subagrupador_valores = dict()

    for servidor in task.iterate(servidores_qs):
        item = dict(nome=servidor.nome, matricula=servidor.matricula)
        for campo in campos_selecionados:
            if campo == 'foto':
                valor = servidor.foto and servidor.foto.url_75x100 or '/static/comum/img/default.jpg'
            elif campo == 'endereco':
                item['Logradouro'] = servidor.endereco_logradouro
                item['Numero'] = servidor.endereco_numero
                item['Complemento'] = servidor.endereco_complemento
                item['Bairro'] = servidor.endereco_bairro
                item['Municipio'] = servidor.endereco_municipio
                item['CEP'] = servidor.endereco_cep
            else:
                if campo == 'ferias':
                    ferias_lista = servidor.ferias_lista
                    valor = []
                    valor.append('<ul>')
                    for ferias in ferias_lista:
                        valor.append(f'<li>{ferias}</li>')
                    valor.append('</ul>')
                    valor = ''.join(valor)
                else:

                    valor = getattr(servidor, str(campo))
                    if callable(valor):
                        valor = valor()
                    if valor is None or valor == '':
                        valor = 'Nenhum'
                if campo == cleaned_data['agrupador']:
                    agrupador_valores[str(valor)] = hasattr(valor, 'id') and valor.id or str(valor)
                if campo == cleaned_data['subagrupador']:
                    subagrupador_valores[str(valor)] = hasattr(valor, 'id') and valor.id or str(valor)
                item[str(campo)] = str(valor)
        servidores_dict.append(item)

    if cleaned_data['subagrupador']:  # 2 agrupamentos
        todos_valores_agrupador = list({i.get(cleaned_data['agrupador']) or 'Nenhum' for i in servidores_dict})
        todos_valores_agrupador.sort()
        todos_valores_subagrupador = list({i.get(cleaned_data['subagrupador']) or 'Nenhum' for i in servidores_dict})
        todos_valores_subagrupador.sort()
        servidores_dict = group_by(servidores_dict, cleaned_data['agrupador'], cleaned_data['subagrupador'], as_dict=1)
        matriz = [[dict(valor='')] + [dict(valor=a) for a in todos_valores_agrupador] + [dict(valor='Total')]]

        for s in todos_valores_subagrupador:
            linha_a = [dict(valor=s)]
            for a in todos_valores_agrupador:
                count = len(servidores_dict[a]['subgroups_as_dict'].get(s, dict(items=[]))['items'])
                url = '{}&{}={}&{}={}&agrupador=&subagrupador='.format(
                    url_base, cleaned_data['agrupador'], agrupador_valores[str(a)], cleaned_data['subagrupador'], subagrupador_valores[str(s)]
                )
                linha_a.append(dict(valor=count, url=url))
            linha_a.append(dict(valor=sum(i['valor'] for i in linha_a[1:])))
            matriz.append(linha_a)
        linha_total = [dict(valor='TOTAL')]
        for a in todos_valores_agrupador:
            linha_total.append(dict(valor=len(servidores_dict[a]['items'])))
        linha_total.append(dict(valor=sum(i['valor'] for i in linha_total[1:])))
        matriz.append(linha_total)
        return render_html_file('rh/templates/servidor_buscar_2_agrupamentos.html', dict(matriz=matriz), request, task)

    elif cleaned_data['agrupador']:  # 1 agrupamento
        dicionario = dict()
        if servidores_dict:
            servidores_agrupados = group_by(servidores_dict, cleaned_data['agrupador'])
            for g in servidores_agrupados:
                g['title'] = '{} ({:d})'.format(g['group'], len(g['items']))
            campo_agrupador_from_alias = _get_alias_campo(cleaned_data['agrupador'])
            grafico = PieChart('grafico', title=f'Servidores por {campo_agrupador_from_alias}', data=[(str(i['group']), len(i['items'])) for i in servidores_agrupados])
            cabecalhos = []
            for cabecalho in servidores_agrupados[0]['items'][0]:
                cabecalhos.append(_get_alias_campo(cabecalho))

            dicionario = dict(
                grafico=grafico,
                servidores=servidores_agrupados,
                campo_agrupador_from_alias=campo_agrupador_from_alias,
                campo_agrupador=cleaned_data['agrupador'],
                cabecalhos=cabecalhos,
            )
        return render_html_file('rh/templates/servidor_buscar_1_agrupamento.html', dicionario, request, task)

    else:  # Nenhum agrupamento
        novos_campos_selecionados = []
        for campo in campos_selecionados:
            if campo == 'endereco':
                novos_campos_selecionados.append('Logradouro')
                novos_campos_selecionados.append('Numero')
                novos_campos_selecionados.append('Complemento')
                novos_campos_selecionados.append('Bairro')
                novos_campos_selecionados.append('Municipio')
                novos_campos_selecionados.append('CEP')
            else:
                novos_campos_selecionados.append(str(campo))
        dicionario = dict(campos_selecionados=novos_campos_selecionados, servidores=servidores_dict, url_csv=url_csv, url_xls=url_xls, url_zip=url_zip)
        return render_html_file('rh/templates/tela_relatorio.html', dicionario, request, task)
