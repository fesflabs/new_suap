import os

from djtools.management.commands import BaseCommandPlus
from pesquisa.models import FotoProjeto, RegistroExecucaoEtapa


def make_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def copy_dir(eh_fotoprojeto=False):

    if eh_fotoprojeto:
        nomes_de_arquivo_origem = FotoProjeto.objects.all()

        destino = 'upload/pesquisa/fotos/'
    else:
        nomes_de_arquivo_origem = RegistroExecucaoEtapa.objects.filter(arquivo__isnull=False).exclude(arquivo='')
        destino = 'upload/pesquisa/atividades/comprovantes/'

    for path_arquivo_origem in nomes_de_arquivo_origem:
        path_arquivo_origem.imagem.save(destino + path_arquivo_origem.imagem.name.split('/')[-1], path_arquivo_origem.imagem.read())
        path_arquivo_origem.save()


class Command(BaseCommandPlus):
    def handle(self, *args, **options):

        copy_dir(eh_fotoprojeto=True)
        copy_dir(eh_fotoprojeto=False)
