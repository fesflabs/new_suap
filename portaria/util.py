# -*- coding: utf-8 -*-

from comum.models import Configuracao
from comum.utils import get_uo
from djtools.utils import to_ascii
from portaria.models import ConfiguracaoSistemaPortaria


def get_configuracao(cfg):
    uo = get_uo()
    try:
        config = ConfiguracaoSistemaPortaria.objects.get(campus=uo)

        if cfg == 'cracha_obrigatorio':
            return config.cracha_obrigatorio
        if cfg == 'habilitar_camera':
            return config.habilitar_camera
        if cfg == 'habilitar_geracao_chave_wifi':
            return config.habilitar_geracao_chave_wifi
        if cfg == 'url_wifi':
            return config.url_wifi or Configuracao.get_valor_por_chave('integracao_wifi', 'url_wifi')
        if cfg == 'limite_compartilhamento_chave' and config.limite_compartilhamento_chave:
            return config.limite_compartilhamento_chave

        raise Exception('A configuração ({} ) não existe ou não tem valor cadastrado para o campus {}'.format(cfg, uo))
    except Exception as e:
        raise Exception('Erro na configuração: {}'.format(e))


def formatar_vinculo_ifrn(palavra):
    return to_ascii(palavra).replace(" ", "_").replace("-", "_").upper()
