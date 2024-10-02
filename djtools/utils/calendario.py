# -*- coding: utf-8 -*-
from datetime import timedelta, date, datetime

__all__ = ['somarDias', 'dateToStr', 'datetimeToStr', 'getNomeMes', 'ehBissexto', 'getUltimoDia', 'getUltimoDiaMes', 'getDataExtenso']


def somarDias(data, qtdDias):
    """
    Soma **qtdDias** a data passada.

    Args:
        data (date|datetime): data para o cálculo;
        qtdDias (int): número de dias a somar.

    Returns:
        Date/Datetime acrescido de **qtdDias**.
    """
    t = timedelta(qtdDias)
    return data + t


def dateToStr(data=None):
    """
    Converte um **date** em uma string no formato dd/mm/aaaa.

    Args:
        date (date): data a ser convertida.

    Returns:
        String com a data passada convertida.
    """
    if data is None:
        data = datetime.today()
    return data.strftime("%d/%m/%Y")


def datetimeToStr(datahora=None):
    """
    Converte um **datetime** em uma string no formato dd/mm/aaaa HH/MM/SS.

    Args:
        datahora (date): data a ser convertida.

    Returns:
        String com a data passada convertida.
    """
    if datahora is None:
        datahora = datetime.now()
    return datahora.strftime("%d/%m/%y %H:%M:%S")


def getNomeMes(mes):
    """
    Obtem o nome do mês por extenso.

    Args:
        mes (int): número do mês.

    Returns:
        String com o nome do mês por extenso.
    """
    meses = {
        1: 'Janeiro',
        2: 'Fevereiro',
        3: 'Março',
        4: 'Abril',
        5: 'Maio',
        6: 'Junho',
        7: 'Julho',
        8: 'Agosto',
        9: 'Setembro',
        10: 'Outubro',
        11: 'Novembro',
        12: 'Dezembro'
    }
    return meses[mes]


def ehBissexto(ano):
    """
    Verifica se o ano é bissexto.

    Args:
        ano (int): ano a ser testado.

    Returns:
         True se o ano for bissexto.
    """
    if (ano % 4 == 0 and ano % 100 != 0) or (ano % 400 == 0):
        return True
    return False


def getUltimoDia(mes, ano):
    """
    Obtem o último dia do mês.

    Args:
        mes (int): número do mês;
        ano (int): número do ano.

    Returns:
        Inteiro com o último dia do mês.
    """
    ultimosDias = {1: 31, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}
    if mes == 2:
        if ehBissexto(ano):
            return 29
        else:
            return 28
    else:
        return ultimosDias[mes]


def getUltimoDiaMes(mes, ano):
    """
    Obtem o **date** com o último dia do mês.

    Args:
        mes (int): número com o mês;
        ano (int): número com o ano.

    Returns:
        Retorna um objeto **date** com o último dia do mês.
    """
    return date(ano, mes, getUltimoDia(mes, ano))


def getDataExtenso(data=None):
    """
    Obtem o **date** escrito por extenso.

    Args:
        data (date): data a processar.

    Returns:
         String com o **date** escrito por extenso.
    """
    if data is None:
        data = datetime.today()
    return '%s de %s de %s' % (data.day, getNomeMes(data.month), data.year)
