# -*- coding: utf-8 -*-
import requests
import json
from edu import services
from django.conf import settings


def sincronizar(diario):
    dados = dict(
        campus=services.serialize(diario.turma.curso_campus.diretoria.setor.uo, add_id=True),
        curso=services.serialize(diario.turma.curso_campus, add_id=True),
        turma=services.serialize(diario.turma, add_id=True),
        diario=services.serialize(diario, add_id=True),
        professores=[
            services.serialize(professor_diario, add_id=True) for professor_diario in diario.professordiario_set.all()
        ],
        alunos=[
            services.serialize(matricula_diario.matricula_periodo.aluno, add_id=True) for matricula_diario in
            diario.matriculadiario_set.all()
        ],
        polo=diario.turma.polo and services.serialize(diario.turma.polo, add_id=True) or None,
        componente=services.serialize(diario.componente_curricular, add_id=True)
    )
    headers = {'Authentication': 'Token {}'.format(settings.MOODLE_SYNC_TOKEN)}
    response = requests.post(settings.MOODLE_SYNC_URL, verify=False, data=json.dumps(dados), headers=headers)
    retorno = json.loads(response.text)
    if 'url' in retorno:
        return retorno['url']
    else:
        raise BaseException(retorno['error'])
