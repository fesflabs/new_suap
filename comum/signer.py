# -*- coding: utf-8 -*-

# pip install oscrypto endesive
# apt-get install -y swig

import re
import os
import tempfile
import datetime
from reportlab.pdfgen import canvas
from OpenSSL import crypto
from django.conf import settings
from cryptography.hazmat import backends
from cryptography.hazmat.primitives.serialization import pkcs12
from PIL import Image, ImageDraw, ImageFont
import qrcode
from asn1crypto.cms import ContentInfo
from cryptography.x509.oid import NameOID
from PyPDF2 import PdfFileReader


TRUSTED_CERTS_PEM = []
os.makedirs(settings.TRUSTED_CERTS_DIRECTORY, exist_ok=True)
for file_name in os.listdir(settings.TRUSTED_CERTS_DIRECTORY):
    if file_name.endswith('.pem'):
        with open(os.path.join(settings.TRUSTED_CERTS_DIRECTORY, file_name)) as fp:
            TRUSTED_CERTS_PEM.append(fp.read())


def create_qrcode_image(url, bgcolor='#EEEEEE'):
    """
    Cria uma imagem contendo o Qrcode da URL passada como parâmetro 
    :param url: endereço eletrônico para o qual o qrcode apontará
    :return: objeto de imagem contendo o qrcode
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color='#000000', back_color=bgcolor)
    qr_img.thumbnail((220, 220), Image.ANTIALIAS)
    return qr_img


def load(certificate_path, passwd):
    """
    Carrega a chave privada e o certificado contidos no arquivo PFX/P12 passado como parâmetro
    :param certificate_path: Caminho do arquivo .pfx ou .p12
    :param passwd: Senha do certificado
    :return: tupla contendo a chave privada na posição 0 e o certificado na posição 1
    """
    with open(certificate_path, 'rb') as fp:
        p12 = pkcs12.load_key_and_certificates(fp.read(), passwd.encode(), backends.default_backend())
    return p12


def subject(certificate_path, passwd):
    """
    Extrai os metadados do certificado contido no arquivo PFX/P12 passado como parâmetro
    :param certificate_path: Caminho do arquivo .pfx ou .p12
    :param passwd: Senha do certificado
    :return: dicionário contendo os metadadados presentes no certificado.
    Ex: CN=Carlos Breno Pereira Silva:0477040XXXX,OU=IFRN - Instituto Federal do Rio Grande do Norte,O=ICPEdu,C=BR
    """
    p12 = load(certificate_path, passwd)
    rdns = p12[1].subject.rdns
    data = {}
    OID_NAMES = {
        NameOID.COMMON_NAME: 'CN',
        NameOID.COUNTRY_NAME: 'C',
        NameOID.ORGANIZATION_NAME: 'O',
        NameOID.ORGANIZATIONAL_UNIT_NAME: 'OU',
    }
    for oid in OID_NAMES:
        data[OID_NAMES[oid]] = ''
    for rdn in rdns:
        for attr in rdn._attributes:
            if attr.oid in OID_NAMES:
                data[OID_NAMES[attr.oid]] = attr.value
    return data


def signature_img(validation_url, signer, document_type=None, authentication_code=None, bgcolor='#EEEEEE', title=None):
    """
    Gera a representação visual da assinatura digital no padrão dos documentos eletrônicos do SUAP
    :param validation_url: endereço eletrônico para validação da assinatura
    :param signer: string contendo o nome e cpf do assinante
    :return: caminho do arquivo de imagem contendo a representação visual da assinatura
    """
    w, h = 1200, 240
    date = datetime.datetime.now()
    img = Image.new('RGBA', (w, h), (255, 255, 255))
    img1 = ImageDraw.Draw(img)
    img1.rectangle([(3, 3), (w - 3, h - 3)], fill=bgcolor, outline=bgcolor)
    font = ImageFont.truetype(os.path.join(settings.BASE_DIR, 'comum', 'static/comum/font/MicrosoftSansSerif.ttf'), 25)
    bold = ImageFont.truetype(os.path.join(settings.BASE_DIR, 'comum', 'static/comum/font/MicrosoftSansSerifBold.ttf'), 25)
    height = 20
    text = 'Assinado em {{}} como {}'.format(title.upper()) if title else 'Documento assinado eletronicamente em {} por'
    img1.text(
        (50, height), text.format(date.strftime('%d/%m/%Y as %H:%M')),
        (0, 0, 0), font=font)
    height += 30
    text = '• {}'.format(signer.upper())
    img1.text((80, height), text, (0, 0, 0), font=bold)

    img1.line([(50, 95), (w - 300, 95)], fill='#CCCCCC', width=3)
    text = 'Para comprovar sua autenticidade, faça a leitura do QRCode ou acesse'
    height += 55
    img1.text((50, height), text, (0, 0, 0), font=font)
    height += 30
    text = validation_url
    img1.text((50, height), text, (0, 0, 0), font=font)
    if document_type:
        height += 30
        img1.text((50, height), 'Tipo de Documento:', (0, 0, 0), font=bold)
        img1.text((400, height), document_type, (0, 0, 0), font=font)
    if authentication_code:
        height += 30
        img1.text((50, height), 'Código de Autenticação:', (0, 0, 0), font=bold)
        img1.text((400, height), authentication_code, (0, 0, 0), font=font)
    img.paste(create_qrcode_image(validation_url, bgcolor=bgcolor), (w - 250, 5))
    tmp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    img.save(tmp)
    return tmp.name


# python manage.py shell -c "from comum.signer import stamp; stamp('https://suap.ifrn.edu.br', 'Carlos Breno', 'Diploma', '23BdEX', title='Reitor')"
def stamp(validation_url, signer, document_type=None, authentication_code=None, bgcolor='#EEEEEE', title=None, pdf_file='file.pdf', x_start=0, y_start=0):
    img_file = signature_img(validation_url, signer, document_type=document_type, authentication_code=authentication_code, bgcolor=bgcolor, title=title)
    can = canvas.Canvas('stamp.pdf')
    can.drawImage(img_file, x_start, y_start, width=300, preserveAspectRatio=True, mask='auto')
    can.save()


def dump_certificate(pfx_file_path, passwd):
    """
    Exporta o certicado no formato PEM contido dentro do arquivo PFX/P12 passado como parâmetro
    :param pfx_file_path: caminho do arquivo .pfx/.p12
    :param passwd: senha da chave privada
    :return: string contedo o certificado no formato PEM
    """
    with open(pfx_file_path, 'rb') as pfx:
        cert = crypto.load_pkcs12(pfx.read(), passwd.encode())
    x509 = cert.get_certificate()
    return crypto.dump_certificate(crypto.FILETYPE_PEM, x509).decode()


def expiration_date(pfx_file_path, passwd):
    """
    Extrai a data de validade do certificado contido dentro do arquivo PFX/P12 passado como parâmetro
    :param pfx_file_path: caminho do arquivo .pfx/.p12
    :param passwd: senha da chave privada
    :return: 
    """
    with open(pfx_file_path, 'rb') as pfx:
        cert = crypto.load_pkcs12(pfx.read(), passwd.encode())
    x509 = cert.get_certificate()
    x509info = x509.get_notAfter()
    exp_day = x509info[6:8].decode('utf-8')
    exp_month = x509info[4:6].decode('utf-8')
    exp_year = x509info[:4].decode('utf-8')
    exp_date = '{}-{}-{}'.format(str(exp_day), str(exp_month), str(exp_year))
    return datetime.datetime.strptime(exp_date, '%d-%m-%Y').date()


def sign(pfx_file_path, passwd, pdf_file_path, sign_img=None, suffix='-assinado', page=0, bgcolor='#EEEEEE', x=0, y=0, px=0, py=0, document_type=None, authentication_code=None, title=None):
    """
    Assina digitalmente o PDF passado como parâmetro.
    :param pfx_file_path: caminho do arquivo .pfx/.p12
    :param passwd: senha da chave privada
    :param pdf_file_path: caminho do arquivo PDF a ser assinado
    :param sign_img: flag indicando para adicionar a representação visual da assinatura em formato de imagem
    :param suffix: string que será adicionada ao nome do arquivo após a assintura. Caso não seja informada, a assinatura
        ocorrerá um arquivo temporário dentro da pasta /deploy/media/tmp. Caso seja informada um string vazia, o arquivo
        original será sobrescrito.
    :param page: o número da página no qual a assinatura deve ser inserida. Zero indica a última página.
    :return: o caminho do arquivo assinado
    """
    from endesive.pdf import cms
    pdf = PdfFileReader(open(pdf_file_path, 'rb'))
    page_number = page - 1 if page else pdf.getNumPages() - 1
    pdf_page = pdf.getPage(page_number)
    width, height = pdf_page.mediaBox[2], pdf_page.mediaBox[3]
    width = int(width)
    height = int(height)
    x = width * float(px) / 100 if px else x
    y = height - (height * float(py) / 100 if py else y) - 50
    date = datetime.datetime.now()
    p12 = load(pfx_file_path, passwd)
    with open(pdf_file_path, 'rb') as f:
        datau = f.read()
    signatures = list_certificates(datau)
    data = {
        'aligned': 0,
        'sigflags': 3,
        'sigflagsft': 132,
        'sigpage': page_number,
        'sigbutton': True,
        'sigfield': 'Signature{}'.format(len(signatures)),
        'signature_img_distort': False,  # default True
        'signature_img_centred': False,  # default True
        'contact': '-',
        'location': 'Brasil',
        'signingdate': date.strftime("D:%Y%m%d%H%M%S+00'00'"),
        'reason': 'Assinatura digital'
    }
    signer = p12[1].subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    # remove cpf (:00000000000) if present in the common name
    signer = re.sub(':\\d+', '', signer)
    if sign_img:
        w, h = 250, 50
        sign_img_path = signature_img(
            validation_url='{}/comum/validar_assinatura/'.format(settings.SITE_URL),
            signer=signer, document_type=document_type, authentication_code=authentication_code, bgcolor=bgcolor, title=title
        )
        for i in range(0, len(signatures) + 1):
            data.update(signaturebox=(x + (i * w), y, x + ((i + 1) * w), y + h), signature_img=sign_img_path)

    else:
        signature = 'Assinado eletronicamente por {} em {}'.format(
            signer, date.strftime('%d/%m/%Y as %H:%M')
        )
        top = len(signatures) * 10
        data.update(signaturebox=(10, 0 + top, 800, 20 + top), signature=signature)
    datas = cms.sign(datau, data, p12[0], p12[1], p12[2], 'sha256')
    if suffix is not None:
        pdf_file_path = pdf_file_path.replace('.pdf', '{}.pdf'.format(suffix))
        fp = open(pdf_file_path, 'wb')
    else:
        fp = tempfile.NamedTemporaryFile(suffix='.pdf', dir=settings.TEMP_DIR)
    fp.write(datau)
    fp.write(datas)
    fp.close()
    return fp.name


def list_certificates(data):
    """
    Lista os certificados utilizados em assinaturas anteriores no PDF cujo conteúdo em bytes é passado como parâmetro.
    :param data: bytes referente ao conteúdo do PDF
    :return: lista contento os certificados
    """
    certs = []

    def index_of(n=1):
        if n == 1:
            return data.find(b'/ByteRange')
        else:
            return data.find(b'/ByteRange', index_of(n - 1) + 1)

    for i in range(1, data.count(b'/ByteRange') + 1):
        n = index_of(i)
        start = data.find(b'[', n)
        stop = data.find(b']', start)
        assert n != -1 and start != -1 and stop != -1
        br = [int(i, 10) for i in data[start + 1: stop].split()]
        contents = data[br[0] + br[1] + 1: br[2] - 1]
        datas = bytes.fromhex(contents.decode('utf8'))
        signed_data = ContentInfo.load(datas)['content']
        for cert in signed_data['certificates']:
            certs.append(cert)
    return certs


def verify(pdf_file_path,):
    """
    Valida as assinaturas contidas no arquivo PDF cujo caminho é passado como parâmetro.
    :param pdf_file_path: caminho do arquivo
    :return: lista de assinaturas validadas
    """
    from endesive import pdf
    signers = []
    trusted_cert_pems = []
    trusted_cert_pems.extend(TRUSTED_CERTS_PEM)
    with open(pdf_file_path, 'rb') as fp:
        data = fp.read()
    for cert in list_certificates(data):
        signers.append(cert.native['tbs_certificate']['subject']['common_name'])
    if signers:
        hashok, signatureok, certok = pdf.verify(data, trusted_cert_pems)
        if hashok and signatureok and certok:
            return signers
    return []


# python manage.py shell -c "from comum import signer; signer.test()"
def test():
    # print(verify('/Users/breno/Downloads/6fd8fac6e28a11eb80ea0242ac120013-tmp1rx_btjd.pdf'))
    # return
    x, y = 40, 50
    file_name = 'RegistroEmissaoDiploma'
    pfx_file_path = 'comum/assinatura-digital/carlos_breno_pereira_silva_04770402414-certificate.p12'
    # pem_file_path = 'comum/assinatura-digital/carlos_breno_pereira_silva_04770402414-certificate.pem'
    # pem_file_content = open(pem_file_path).read()
    passwd = ''

    # print(subject(pfx_file_path, passwd))
    # print(expiration_date(pfx_file_path, passwd))
    # print(dump_certificate(pfx_file_path, passwd))

    file_path = sign(
        pfx_file_path=pfx_file_path, passwd=passwd, sign_img=True, bgcolor='#ebf3e5',
        pdf_file_path='comum/assinatura-digital/{}.pdf'.format(file_name),
        document_type='Diploma', authentication_code='A4ceJe', px=x, py=y
    )
    print(file_path)
    return

    pfx_file_path = 'comum/assinatura-digital/placauto.pfx'
    passwd = ''
    file_path = sign(
        pfx_file_path=pfx_file_path, passwd=passwd, sign_img=True, bgcolor='#ebf3e5',
        pdf_file_path='comum/assinatura-digital/{}-assinado.pdf'.format(file_name),
        document_type='Diploma', authentication_code='A4ceJe', x=x, y=y
    )

    print(file_path)
    # print(verify(file_path))
