# coding: utf-8
import os
import base64
import subprocess
import tempfile

from django.conf import settings
from django.template.loader import get_template
from wkhtmltopdf.utils import render_pdf_from_template

from djtools.utils import get_datetime_now


SELO_IMAGEM = os.path.join(settings.BASE_DIR, 'comum', 'static', 'comum', 'img', 'selo-protocolo.png')


def documento_to_pdf(documento):
    from documento_eletronico.views import gerar_codigo_verificador_documento

    template = get_template('imprimir_documento_pdf.html')

    codigo_verificador = gerar_codigo_verificador_documento(documento)

    selo_data = base64.b64encode(open(SELO_IMAGEM, 'rb').read())
    selo_data = 'data:image/png;base64,'.encode() + selo_data

    qrcode_data = documento.qrcode_base64image
    agora = get_datetime_now()
    orientacao = 'portrait'

    conteudo_pdf = render_pdf_from_template(
        template,
        header_template=None,
        footer_template=None,
        context={'agora': agora, 'selo_data': selo_data, 'documento': documento, 'qrcode_data': qrcode_data, 'codigo_verificador': codigo_verificador},
        cmd_options={
            'header-spacing': 3,
            'footer-spacing': 3,
            'orientation': orientacao,
            'page-height': '297mm',
            'page-width': '210mm',
            'header-left': '[title]',
            'header-font-size': 10,
        },
    )

    nome_arquivo = tempfile.mktemp('.pdf')
    with open(nome_arquivo, mode='wb') as arquivo_saida:
        arquivo_saida.write(conteudo_pdf)

    return nome_arquivo


def html_to_pdf(template_name, context):
    template = get_template(template_name)
    conteudo_pdf = render_pdf_from_template(
        template,
        header_template=None,
        footer_template=None,
        context=context,
        cmd_options={'header-spacing': 3, 'footer-spacing': 3, 'page-height': '297mm', 'page-width': '210mm', 'header-left': '[title]', 'header-font-size': 10},
    )

    nome_arquivo = tempfile.mktemp('.pdf')
    with open(nome_arquivo, mode='wb') as arquivo_saida:
        arquivo_saida.write(conteudo_pdf)

    return nome_arquivo


def merge_pdfs(pdfs):
    gs = settings.GHOSTSCRIPT_CMD
    nome_arquivo = tempfile.mktemp('.pdf')

    cmd = [gs, '-dQUIET', '-dNOPAUSE', '-sDEVICE=pdfwrite', '-dBATCH', '-sOutputFile=' + nome_arquivo]
    cmd.extend(pdfs)
    dict_env = {'TMPDIR': settings.TEMP_DIR, 'TEMP': settings.TEMP_DIR}
    subprocess.call(cmd, env=dict_env)
    with open(nome_arquivo, mode='rb') as arquivo_saida:
        content = arquivo_saida.read()
    os.unlink(nome_arquivo)
    return content
