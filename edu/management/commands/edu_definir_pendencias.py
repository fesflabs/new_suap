# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from edu.models import Aluno, SituacaoMatricula, Modalidade


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        qs = Aluno.objects.filter(matriz__isnull=False)
        qs_alunos_fic = qs.filter(curso_campus__modalidade__in=(Modalidade.FIC, Modalidade.PROEJA_FIC_FUNDAMENTAL))
        qs_alunos_fic.filter(situacao=SituacaoMatricula.MATRICULADO).update(pendencia_ch_obrigatoria=True)
        qs_alunos_fic.filter(situacao=SituacaoMatricula.NAO_CONCLUIDO).update(pendencia_ch_obrigatoria=True)
        qs_alunos_fic.filter(situacao=SituacaoMatricula.CONCLUIDO).update(pendencia_ch_obrigatoria=False)

        qs_alunos_regulares = qs.exclude(curso_campus__modalidade=Modalidade.FIC).exclude(curso_campus__modalidade=Modalidade.PROEJA_FIC_FUNDAMENTAL)
        total = qs_alunos_regulares.count()
        for i, o in enumerate(qs_alunos_regulares):
            o.get_situacao()
            o.save()
            if not i % 500:
                print((i * 100 / total, '%'))
