# -*- coding: utf-8 -*-
from django.db.models import Max
from djtools.management.commands import BaseCommandPlus
from auxilioemergencial.models import DocumentoAluno, InscricaoInternet, InscricaoDispositivo, InscricaoMaterialPedagogico


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        for registro in DocumentoAluno.objects.values('aluno').annotate(data=Max('data_cadastro')):
            InscricaoInternet.objects.filter(aluno=registro['aluno']).update(documentacao_atualizada_em=registro['data'])
            InscricaoDispositivo.objects.filter(aluno=registro['aluno']).update(documentacao_atualizada_em=registro['data'])
            InscricaoMaterialPedagogico.objects.filter(aluno=registro['aluno']).update(documentacao_atualizada_em=registro['data'])
