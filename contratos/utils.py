import os
from functools import wraps

from django.conf import settings

from comum.models import Arquivo
from contratos.models import Contrato
from django.contrib.auth.decorators import login_required
from djtools.utils import send_notification


def verificar_diretorio(path, arquivo):
    arquivo_tmp = arquivo.get_arquivo_temporario()
    os.system('mkdir -p {}'.format(path[0: path.rfind('/')]))
    file = open(path, 'wb')
    file.write(arquivo_tmp.read())
    file.close()
    arquivo_tmp.close()
    os.remove(arquivo_tmp.name)


def importar_arquivos():
    root_dir = settings.BASE_DIR
    for arquivo in Arquivo.objects.all():
        if hasattr(arquivo, 'contrato_set'):
            for t in arquivo.contrato_set.all():
                path = root_dir + '/contratos/upload/contrato/{:d}/{:d}.pdf'.format(t.id, t.id)
                verificar_diretorio(path, arquivo)
        if hasattr(arquivo, 'aditivo_set'):
            for t in arquivo.aditivo_set.all():
                path = root_dir + '/contratos/upload/contrato/{:d}/aditivos/{:d}/{:d}.pdf'.format(t.contrato.id, t.id, t.id)
                verificar_diretorio(path, arquivo)
        if hasattr(arquivo, 'anexocontrato_set'):
            for t in arquivo.anexocontrato_set.all():
                path = root_dir + '/contratos/upload/contrato/{:d}/anexos/{:d}/{:d}.pdf'.format(t.contrato.id, t.id, t.id)
                verificar_diretorio(path, arquivo)
        if hasattr(arquivo, 'publicacaoaditivo_set'):
            for t in arquivo.publicacaoaditivo_set.all():
                path = root_dir + '/contratos/upload/contrato/{:d}/aditivos/{:d}/publicacao/{:d}.pdf'.format(t.aditivo.contrato.id, t.aditivo.id, t.id)
                verificar_diretorio(path, arquivo)
        if hasattr(arquivo, 'publicacaocontrato_set'):
            for t in arquivo.publicacaocontrato_set.all():
                path = root_dir + '/contratos/upload/contrato/{:d}/publicacao/{:d}.pdf'.format(t.contrato.id, t.id)
                verificar_diretorio(path, arquivo)


def por_extenso(value):
    from comum.utils import extenso

    if bool(value):
        reais, centavos = str(value).split('.')
        return '{}'.format(extenso(reais, centavos))
    else:
        return '-'


class Notificar:
    @staticmethod
    def informar_pendencias_na_medicao_ao_fiscal(medicao):
        """ Enviando email, notificando Fiscal de Contrato sobre pendências em determinada medição"""
        contrato = medicao.parcela.cronograma.contrato
        titulo = '[SUAP] Contratos: Medição com pendências'
        texto = []
        texto.append('<h1>Medição de Contrato com Pendências</h1>')
        texto.append('<h2>Contrato: {}</h2>'.format(contrato))
        texto.append('<h3>Seguem as pendências informadas pelo Gerente do Contrato:</h3>')

        for medicao_documento in medicao.medicaotipodocumentocomprobatorio_set.filter(recebido_gerente="Pendente"):
            texto.append('<dl>')
            texto.append('<dt>Documento:</dt><dd>{}</dd>'.format(medicao_documento.tipo_documento_comprobatorio.descricao))
            texto.append('<dt>Pendência:</dt><dd>{}</dd>'.format(medicao_documento.parecer_gerente))
            texto.append('</dl>')
        texto.append('<p>--</p>')
        texto.append('<p>Acessar medição: <a href="{0}">{0}</a></p>'.format("{}{}".format(settings.SITE_URL, medicao.get_update_url())))
        send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [medicao.fiscal.servidor.get_vinculo()])

    @staticmethod
    def contrato_sem_garantia_vinculada(contrato):
        titulo = '[SUAP] Contratos: Aviso - Adicione arquivo da Garantia contratual'

        categoria = f"Adicione arquivo da garantia - Contrato {contrato.numero}"
        texto = []
        texto.append('<h1>{}</h1>'.format(categoria))
        texto.append(f'<p>O contrato {contrato.numero} foi cadastrado com exigência de garantia contratual, '
                     f'porém ainda não existe nenhhum arquivo de Garantia vinculado')
        texto.append('<p>Acesse o Contrato e adicione os arquivos na aba Garantias</p>')
        texto.append('<h3>Dados Gerais</h3>')
        texto.append('<dl>')
        texto.append('<dt>Contrato:</dt><dd>{}</dd>'.format(contrato))
        texto.append('<dt>Processo Eletrônico:</dt><dd>{}</dd>'.format(contrato.processo))
        texto.append('<dt>Data de Início:</dt><dd>{}</dd>'.format(contrato.data_inicio.strftime("%d/%m/%Y")))
        texto.append('</dl>')
        texto.append('<p>--</p>')
        texto.append('<p>Para mais informações, acesse: <a href="{0!s}?tab=7">{0!s}</a></p>'.format(contrato.get_absolute_url()))

        vinculos_fiscais_atuais = [fiscal.servidor.get_vinculo() for fiscal in contrato.get_fiscais_atuais()]

        send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, vinculos_fiscais_atuais, categoria=categoria)


def verificar_fiscal(modelo=None):
    def verificar_fiscal_part(func):
        @login_required
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            from djtools.utils import httprr
            from django.shortcuts import get_object_or_404
            if modelo:
                objeto = get_object_or_404(modelo, pk=list(kwargs.values())[0])
                contrato = getattr(objeto, 'contrato')
            else:
                contrato = get_object_or_404(Contrato, pk=kwargs.get('contrato_id'))
            fiscal = contrato.get_fiscal(request.user.get_relacionamento())
            if not fiscal:
                return httprr('/contratos/contrato/{}/'.format(contrato.id), 'Você não é fiscal desse contrato.', tag='error', close_popup=True)
            return func(request, *args, **kwargs)
        return wrapper
    return verificar_fiscal_part
