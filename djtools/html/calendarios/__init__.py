import html
from calendar import HTMLCalendar
from collections import OrderedDict
from datetime import datetime

from comum.utils import daterange


class Calendario(HTMLCalendar):
    meses_extenso = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    eventos = OrderedDict()
    eventos_por_mes = OrderedDict()
    tipos_eventos_calendario = OrderedDict()
    mostrar_mes_ano_cabecalho_mes = False

    def adicionar_tipo_evento(self, css, tipo_evento):
        if not css in self.tipos_eventos_calendario:
            self.tipos_eventos_calendario[css] = str(tipo_evento)

    def resetar_listas(self):
        self.eventos = OrderedDict()
        self.eventos_por_mes = OrderedDict()
        self.tipos_eventos_calendario = OrderedDict()
        self.tipos_eventos_calendario['hoje'] = 'Hoje'
        if self.tipos_eventos_default:
            self.tipos_eventos_calendario['evento'] = 'Evento/Data Comemorativa'
            self.tipos_eventos_calendario['extra'] = 'Liberação Por Documento Legal / Parcial'
            self.tipos_eventos_calendario['ferias'] = 'Férias'
            self.tipos_eventos_calendario['recesso'] = 'Recesso'
            self.tipos_eventos_calendario['feriado'] = 'Feriado'

    def __init__(self, firstweekday=6, tipos_eventos_default=True):
        self.firstweekday = firstweekday
        self.tipos_eventos_default = tipos_eventos_default
        self.resetar_listas()

    def retirar_numeros_string(self, valor):
        for num in range(0, 10):
            valor = valor.replace(str(num), "")
        return valor

    def existe_padrao_numerico(self, lista_css, padrao):
        lista = lista_css.split()
        for css in lista:
            css_padrao = self.retirar_numeros_string(css)
            css_padrao = css_padrao.split("_")[0]
            if css_padrao != padrao:
                return False
        return True

    def adicionar_evento_calendario(self, data_inicio, data_fim, descricao, css_class, title=''):
        """
        Metodo que montará o evento no calendario.
        """
        # Tratamento do CSS
        if data_inicio == data_fim:
            if self.eventos.get(str(data_inicio)):
                if not css_class in self.eventos.get(str(data_inicio))['css']:
                    self.eventos[str(data_inicio)]['css'] += ' ' + css_class

                if len(self.eventos.get(str(data_inicio))['css']) >= 2:
                    padrao_css = self.retirar_numeros_string(css_class)

                    if self.existe_padrao_numerico(self.eventos.get(str(data_inicio))['css'], self.retirar_numeros_string(css_class)):
                        if not "{}_conflito_leve".format(padrao_css) in self.eventos.get(str(data_inicio))['css']:
                            self.eventos[str(data_inicio)]['css'] += ' {}_conflito_leve'.format(padrao_css)
                        else:
                            self.eventos[str(data_inicio)]['css'] += ' {}_conflito_varios'.format(padrao_css)

                self.eventos[str(data_inicio)]['title'] += ' {}'.format(title)

            else:
                self.eventos[str(data_inicio)] = dict(data=data_inicio, css=css_class, title=title)

        elif data_fim:
            for data in daterange(data_inicio, data_fim):
                if self.eventos.get(str(data)):
                    if not css_class in self.eventos.get(str(data))['css']:
                        self.eventos[str(data)]['css'] += ' ' + css_class

                    if len(self.eventos.get(str(data))['css']) >= 2:
                        padrao_css = self.retirar_numeros_string(css_class)

                        if self.existe_padrao_numerico(self.eventos.get(str(data))['css'], self.retirar_numeros_string(css_class)):
                            if not "{}_conflito_leve".format(padrao_css) in self.eventos.get(str(data))['css']:
                                self.eventos[str(data)]['css'] += ' {}_conflito_leve'.format(padrao_css)
                            else:
                                self.eventos[str(data)]['css'] += ' {}_conflito_varios'.format(padrao_css)

                    self.eventos[str(data)]['title'] += ' | {}'.format(title)
                else:
                    self.eventos[str(data)] = dict(data=data, css=css_class, title=title)

        descricao = html.escape(descricao)
        #   Tratamento dos Eventos Verificar se as datas inicial e final estao no mesmo mês e ano
        if data_inicio and data_fim:
            if data_inicio.year == data_fim.year:
                if data_inicio.month == data_fim.month:
                    ano_mes = str(data_inicio.year) + str(data_inicio.month)
                    if not self.eventos_por_mes.get(ano_mes):
                        self.eventos_por_mes[ano_mes] = []
                    self.eventos_por_mes[ano_mes].append(dict(data_inicio=data_inicio, data_fim=data_fim, descricao=descricao, css=css_class, title=title))
                else:
                    for mes in range(data_inicio.month, data_fim.month + 1):
                        if not self.eventos_por_mes.get(str(data_inicio.year) + str(mes)):
                            self.eventos_por_mes[str(data_inicio.year) + str(mes)] = []
                        self.eventos_por_mes[str(data_inicio.year) + str(mes)].append(dict(data_inicio=data_inicio, data_fim=data_fim, descricao=descricao, css=css_class, title=title))
            else:
                for mes in range(data_inicio.month, 13):
                    if not self.eventos_por_mes.get(str(data_inicio.year) + str(mes)):
                        self.eventos_por_mes[str(data_inicio.year) + str(mes)] = []
                    self.eventos_por_mes[str(data_inicio.year) + str(mes)].append(dict(data_inicio=data_inicio, data_fim=data_fim, descricao=descricao, css=css_class, title=title))

                for mes in range(1, data_fim.month + 1):
                    if not self.eventos_por_mes.get(str(data_fim.year) + str(mes)):
                        self.eventos_por_mes[str(data_fim.year) + str(mes)] = []
                    self.eventos_por_mes[str(data_fim.year) + str(mes)].append(dict(data_inicio=data_inicio, data_fim=data_fim, descricao=descricao, css=css_class, title=title))

    def montar_dia(self, dia, dia_da_semana, mes, ano):
        """
        Retorna o dia como um tipo <td>
        """
        if dia == 0:
            return self.celula_do_dia('', '', '&nbsp;', dia_da_semana)
        else:
            cssclass = []
            titles = []
            hoje = datetime.now()
            if hoje.day == dia and hoje.month == mes and hoje.year == ano:
                cssclass.append('hoje')
            if dia_da_semana == 5 or dia_da_semana == 6:
                cssclass.append('fds')

            data = []
            data.append(str(dia))
            data.append(str(mes))
            data.append(str(ano))
            try:
                data = datetime.strptime('-'.join(data), "%d-%m-%Y").date()
                if self.eventos.get(str(data)):
                    cssclass.append(self.eventos[str(data)]['css'])
                    titles.append(self.eventos[str(data)].get('title') or self.eventos[str(data)]['css'].title())
            except Exception:
                pass
            return self.celula_do_dia(' '.join(cssclass), '&#13;'.join(titles), dia, dia_da_semana)  # '&#13;' quebra a linha no title

    def celula_do_dia(self, cssclass, titles, dia, dia_da_semana, conteudo=''):
        celula_dia = []
        if dia_da_semana == 0:
            semana = 'calendario-segunda'
        elif dia_da_semana == 1:
            semana = 'calendario-terca'
        elif dia_da_semana == 2:
            semana = 'calendario-quarta'
        elif dia_da_semana == 3:
            semana = 'calendario-quinta'
        elif dia_da_semana == 4:
            semana = 'calendario-sexta'
        elif dia_da_semana == 5:
            semana = 'calendario-sabado'
        elif dia_da_semana == 6:
            semana = 'calendario-domingo'
            celula_dia.append('<tr>')

        if dia:
            dia = '<span>%s</span>' % dia

        celula_dia.append('<td class="{}" title="{}" headers="{}">{}{}</td>'.format(cssclass, titles, semana, dia, conteudo))
        if dia_da_semana == 5:
            celula_dia.append('</tr>')

        return '\n'.join(celula_dia)

    def montar_calendario_mes(self, mes, ano):
        html_code = ['<div class = "calendario">']
        html_code.append('<table class="calendario-dias">')
        if self.mostrar_mes_ano_cabecalho_mes:
            html_code.append('<caption>{}/{}</caption>'.format(self.meses_extenso[int(mes) - 1], ano))
        else:
            html_code.append('<caption>%s</caption>' % self.meses_extenso[int(mes) - 1])

        html_code.append('<thead>')
        html_code.append('<tr>')
        html_code.append('<th id="calendario-domingo">Dom</th>')
        html_code.append('<th id="calendario-segunda">Seg</th>')
        html_code.append('<th id="calendario-terca">Ter</th>')
        html_code.append('<th id="calendario-quarta">Qua</th>')
        html_code.append('<th id="calendario-quinta">Qui</th>')
        html_code.append('<th id="calendario-sexta">Sex</th>')
        html_code.append('<th id="calendario-sabado">Sab</th>')
        html_code.append('</tr>')
        html_code.append('</thead>')
        html_code.append('<tbody>')
        return '\n'.join(html_code)

    def fechar_calendario_mes(self):
        html_code = ['</tbody></table>']
        return '\n'.join(html_code)

    def legenda_tipos_eventos(self):
        html_code = []
        html_code.append('<div class="legenda">')
        html_code.append('<p>Legenda:</p>')
        html_code.append('<ul>')
        for css_evento in self.tipos_eventos_calendario:
            html_code.append('<li class="{}">{}</li>'.format(css_evento, self.tipos_eventos_calendario.get(css_evento)))

        html_code.append('</ul>')
        html_code.append('</div>')
        return '\n '.join(html_code)

    def fechar_div_calendario_mes(self):
        html_code = ['</div>']
        return '\n'.join(html_code)

    def montar_legenda(self, mes, ano):
        ano_mes = str(ano) + str(mes)
        if self.eventos_por_mes.get(ano_mes):
            html_code = ['<ul class="calendario-referencia">']
            #
            eventos = self.eventos_por_mes.get(ano_mes)
            eventos_clean = []
            for evento in eventos:
                if not (evento in eventos_clean):  # remove eventos IDÊNTICOS
                    eventos_clean.append(evento)
            eventos_clean = sorted(eventos_clean, key=lambda e: e['data_inicio'])  # ordena por data_inicio
            #
            for evento in eventos_clean:
                if evento['data_inicio'] == evento['data_fim'] or evento['data_fim'] is None:
                    html_code.append('<li class="{}">Dia {}: {}</li>'.format(evento['css'], str(evento['data_inicio'].day), evento['descricao']))
                else:
                    html_code.append(
                        '<li class="%s">De %s/%s a %s/%s: %s</li>'
                        % (
                            evento['css'],
                            str(evento['data_inicio'].day),
                            str(evento['data_inicio'].month),
                            str(evento['data_fim'].day),
                            str(evento['data_fim'].month),
                            evento['descricao'],
                        )
                    )
            html_code.append('</ul>')
            return '\n'.join(html_code)
        return ' '

    def formato_mes(self, ano, mes):
        html_code = self.montar_calendario_mes(mes, ano)
        for semana in self.monthdays2calendar(ano, mes):
            for dia, dia_da_semana in semana:
                html_code += self.montar_dia(dia, dia_da_semana, mes, ano)

        html_code += self.fechar_calendario_mes()
        html_code += self.montar_legenda(mes, ano)
        html_code += self.fechar_div_calendario_mes()
        return html_code

    def formato_ano(self, ano):
        html_code = []
        html_code.append(self.legenda_tipos_eventos())
        for cont in range(12):
            if cont == 0:
                html_code.append(self.abrir_div_container())
            html_code.append(self.formato_mes(ano, cont + 1))
            if cont == 11:
                html_code.append(self.fechar_div_container())

        return ' '.join(html_code)

    def formato_ano_calendario_compras(self, ano):
        html_code = []
        for cont in range(12):
            if cont == 0:
                html_code.append(self.abrir_div_container())
            html_code.append(self.formato_mes(ano, cont + 1))
            if cont == 11:
                html_code.append(self.fechar_div_container())

        return ' '.join(html_code)

    def formato_periodo(self, mes_inicio, ano_inicio, mes_fim, ano_fim):
        html_code = []
        mes_inicial_ano = mes_inicio
        for ano in range(ano_inicio, ano_fim + 1):
            mes_final_ano = 12
            if ano == ano_fim:
                mes_final_ano = mes_fim

            for mes in range(mes_inicial_ano, mes_final_ano + 1):
                html_code.append(self.formato_mes(ano, mes))

            mes_inicial_ano = 1  # recomeça em janeiro

        return ' '.join(html_code)

    def abrir_div_container(self):
        html_code = []
        html_code.append('<div class="calendarios-container">')
        return ' '.join(html_code)

    def fechar_div_container(self):
        html_code = []
        html_code.append('</div>')
        return ' '.join(html_code)

    def __str__(self):
        return self.formato_ano(datetime.today().year)


class CalendarioPlus(Calendario):
    mostrar_mes_e_ano = False  # cabeçalho do calendário de um mês --> ex.'Outubro/2013' ou 'Outubro'
    destacar_hoje = True
    destacar_fim_de_semana = True
    ocultar_titles_dia = False
    ocultar_legenda_eventos = False
    envolve_mes_em_um_box = False

    def adicionar_evento_calendario(self, data_inicio, data_fim, descricao, css_class, title=None, dia_todo=None, url=None):
        """
        Metodo que montará o evento no calendario.
        """
        # garante que as datas serão do tipo datetime
        if not type(data_inicio) is datetime:
            # redefine data_inicio
            data_inicio = datetime(data_inicio.year, data_inicio.month, data_inicio.day, 0, 0, 0)  # hour,minute,second

        if not data_fim:
            data_fim = data_inicio
        else:
            if not type(data_fim) is datetime:
                # redefine data_fim
                data_fim = datetime(data_fim.year, data_fim.month, data_fim.day, 0, 0, 0)  # hour,minute,second

        # nesse ponto, as datas são datetime

        '''
            eventos = {'todos': [{},{},{}],
                       'ano-mes': [{},{},{}]}
            evento = {
                        'data_inicio': dia/mes/ano hora:min:sec,
                        'data_fim': dia/mes/ano hora:min:sec,
                        'descricao_evento': 'evento 1',
                        'css_class': 'css_class 1',
                        'title': '?',
                        'url': None
                     }

            'ano-mes' obtido de data_inicio

            ** possibilidade de eventos paralelos em um mesmo dia

            Montando o mês:
             _____________
            |  mês[/ano]  |
             -------------
            | dias        |
             -------------

            Montando o dia:
                - hoje?
                    [css hoje]
                - fim de semana?
                    [css fds]
                - aplicar css_class do último evento (por enquanto 09/10/2013)
                    - eventos do dia/mês/ano --> eventos['todos'][evento X][data_inicio] <= dia/mes/ano <= eventos['todos'][evento X][data_fim]
                        - último evento
                            - aplicar css_class
                - [titles]
                    - eventos do dia/mês/ano --> eventos['todos'][evento X][data_inicio] <= dia/mes/ano <= eventos['todos'][evento X][data_fim]
                        - para cada evento
                            - concatena 'title' ou 'css_class'
                    - aplica concatenação

            [Montando a legenda do mês]
                - eventos do mês/ano --> eventos['ano-mes']
                    - para cada evento
                        - data_inicio = data_fim
                            - Dia X[,hora:min inicio à hora:min fim]: descricao_evento
                        - data_inicio <> data_fim
                            - mesmo mês?
                                - Dia X[, hora:min inicio] até Dia Y[, hora:min fim]: descricao_evento
                            - meses diferentes
                                - Dia X/mês A[, hora:min inicio] até Dia Y/mês B[, hora:min fim]: descricao_evento
                        - aplica css_class

            obtendo calendários:
                - obter calendário de um mês específico (mes/ano)
                    - monta o mês/ano
                - obter calendários de um ano específico (ano)
                    monta o ano
                        monta jan/ano
                        monta fev/ano
                        ...
                        monta dez/ano
                - obter calendários de um período específico (mes/ano inicio, mes/ano fim)
        '''

        evento = dict(data_inicio=data_inicio, data_fim=data_fim, descricao_evento=descricao, css_class=css_class, title=title, dia_todo=dia_todo, url=url)
        # todos
        if 'todos' not in self.eventos:
            self.eventos['todos'] = []
        self.eventos['todos'].append(evento)

        # por mês
        ano_mes = str(data_inicio.date().year) + str(data_inicio.date().month)
        if ano_mes not in self.eventos:
            self.eventos[ano_mes] = []
        self.eventos[ano_mes].append(evento)

    def eventos_da_data(self, data):
        eventos = []
        if 'todos' in self.eventos:
            # garante que 'data' seja um 'date'
            if type(data) is datetime:
                data = data.date()
            for evento in self.eventos['todos']:
                if data >= evento['data_inicio'].date() and data <= evento['data_fim'].date():
                    eventos.append(evento)
        return eventos

    def montar_dia(self, dia, dia_da_semana, mes, ano):
        """
        Retorna o dia como um tipo <td>
        """
        if dia == 0:
            return self.celula_do_dia('vazio', '', '', dia_da_semana)
        else:
            cssclass = set()
            if self.destacar_hoje:
                hoje = datetime.now()
                if hoje.day == dia and hoje.month == mes and hoje.year == ano:
                    cssclass.add('hoje')

            if self.destacar_fim_de_semana:
                if dia_da_semana == 5 or dia_da_semana == 6:
                    cssclass.add('fds')

            data = []
            data.append(str(dia))
            data.append(str(mes))
            data.append(str(ano))
            data = datetime.strptime('-'.join(data), "%d-%m-%Y").date()
            eventos = sorted(self.eventos_da_data(data), key=lambda e: e['data_inicio'])
            cssclass.add(self.eh_dia_todo(eventos, data))
            conteudo = self.montar_eventos(eventos)
            return self.celula_do_dia(' '.join(cssclass), '', dia, dia_da_semana, conteudo)

    def eh_dia_todo(self, eventos, data):
        if len(eventos) <= 1:
            for evento in eventos:
                if evento['dia_todo']:
                    return evento['css_class']

        return ''

    def qtd_cssclass(self, cssclass):
        """
        Retorna a quantidade de classes dos eventos, ou seja, excluindo os colocados pelo calendário (hoje e fds)
        """
        cssclass_extra = cssclass.copy()
        cssclass_extra.discard('hoje')
        cssclass_extra.discard('fds')
        return len(cssclass_extra)

    def montar_calendario_mes(self, mes, ano):
        html_code = ['<div class="calendario calendario-mensal">']
        html_code.append('<table>')
        if not self.envolve_mes_em_um_box:
            if self.mostrar_mes_e_ano:
                html_code.append('<caption>{}/{}</caption>'.format(self.meses_extenso[int(mes) - 1], ano))
            else:
                html_code.append('<caption>%s</caption>' % self.meses_extenso[int(mes) - 1])
        html_code.append('<thead>')
        html_code.append('<tr>')
        html_code.append('<th class="semana">Dom</th>')
        html_code.append('<th class="semana">Seg</th>')
        html_code.append('<th class="semana">Ter</th>')
        html_code.append('<th class="semana">Qua</th>')
        html_code.append('<th class="semana">Qui</th>')
        html_code.append('<th class="semana">Sex</th>')
        html_code.append('<th class="semana">Sab</th>')
        html_code.append('</tr>')
        html_code.append('</thead>')
        html_code.append('<tbody>')
        return '\n'.join(html_code)

    def montar_eventos(self, eventos):
        legendas = list()
        for evento in eventos:
            descricao = evento['descricao_evento']
            url = evento.get('url')
            extra = url and 'style="cursor:pointer" onclick="popup(\'{}\')"'.format(url) or ''
            legendas.append('<li {} class="{}" title="{}">{}</li>'.format(extra, evento['css_class'], evento['title'], descricao))

        html_code = ['<ul class="calendario-eventos">'] + legendas + ['</ul>']
        return '\n'.join(html_code)

    def formato_mes(self, ano, mes):
        html_code = self.montar_calendario_mes(mes, ano)
        for semana in self.monthdays2calendar(ano, mes):
            for dia, dia_da_semana in semana:
                html_code += self.montar_dia(dia, dia_da_semana, mes, ano)
        html_code += self.fechar_calendario_mes()
        html_code += self.fechar_div_calendario_mes()
        if self.envolve_mes_em_um_box:
            if self.mostrar_mes_e_ano:
                title_box = '{}/{}'.format(self.meses_extenso[int(mes) - 1], ano)
            else:
                title_box = '{}'.format(self.meses_extenso[int(mes) - 1])
            html_code = '<div class="box"><h3>{}</h3>{}</div>'.format(title_box, html_code)
        return html_code

    def formato_periodo(self, mes_inicio, ano_inicio, mes_fim, ano_fim, omite_mes_sem_eventos=False):
        html_code = []
        mes_inicial_ano = mes_inicio
        for ano in range(ano_inicio, ano_fim + 1):
            mes_final_ano = 12
            if ano == ano_fim:
                mes_final_ano = mes_fim
            for mes in range(mes_inicial_ano, mes_final_ano + 1):
                if omite_mes_sem_eventos:
                    omite_mes = True
                    if 'todos' in self.eventos:
                        for evento in self.eventos['todos']:
                            if evento['data_inicio'].month == mes and evento['data_inicio'].year == ano or evento['data_fim'].month == mes and evento['data_fim'].year == ano:
                                omite_mes = False
                                break
                    if omite_mes:
                        continue
                #
                html_code.append(self.formato_mes(ano, mes))
            mes_inicial_ano = 1  # recomeça em janeiro
        return ' '.join(html_code)
