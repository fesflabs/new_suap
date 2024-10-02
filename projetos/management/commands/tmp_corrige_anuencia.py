# -*- coding: utf-8 -*-
"""
Comando para preencher os responsáveis pela anuência da chefia
"""
from djtools.management.commands import BaseCommandPlus
from projetos.models import Projeto, Participacao
import datetime
import tqdm


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        for projeto in tqdm.tqdm(Projeto.objects.filter(edital__inicio_inscricoes__year=2022)):
            p = Participacao.objects.get(projeto=projeto, responsavel=True)
            if p.exige_anuencia() and not p.responsavel_anuencia:
                servidor = p.vinculo_pessoa.relacionamento
                chefes = servidor.funcionario.chefes_na_data(datetime.datetime.now().date())
                if chefes:
                    p.responsavel_anuencia = chefes[0].servidor
                    p.save()
