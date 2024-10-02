from django.conf import settings
from arquivo.models import Processo, TipoArquivo
import os


def importar_tipo_arquivo():
    arquivo = os.path.join(settings.BASE_DIR, 'arquivo/static/arquivo/tipo_arquivo.txt')
    txt_file = open(arquivo, 'r')
    txt_linhas = txt_file.readlines()
    for linha in txt_linhas:
        tipo = linha.split("&&")[0].strip()
        if linha.split("&&")[1].find(":") != -1:
            processo_superior, created = Processo.objects.get_or_create(descricao=linha.split("&&")[1].split(":")[0].strip())
            processo, created = Processo.objects.get_or_create(descricao=linha.split("&&")[1].split(":")[1].strip())
            processo.superior = processo_superior
            processo.save()
        else:
            processo, created = Processo.objects.get_or_create(descricao=linha.split("&&")[1].strip())
        tipo_arquivo, created = TipoArquivo.objects.get_or_create(descricao=tipo)
        if not tipo_arquivo in processo.tipos_arquivos.all():
            processo.tipos_arquivos.add(tipo_arquivo)
    txt_file.close()
