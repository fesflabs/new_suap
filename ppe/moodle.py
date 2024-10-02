# -*- coding: utf-8 -*-

import json

import requests
from django.conf import settings
from sc4net import get

from ppe import services


def verificar_curso(nome_breve_curso_moodle):

    try:
        response = get(f'{settings.MOODLE_URL_API}/?get_curso&curso={nome_breve_curso_moodle}',
                       headers={'Authentication': f'Token {settings.MOODLE_SYNC_TOKEN}'})
        # print(json.loads(response))
        retorno = json.loads(response)
    except Exception as e:
        raise BaseException(f"Erro na integração. O Moodle disse: {e}")

    if retorno:
        return retorno
    else:
        raise BaseException(retorno['error'])

def enviar_dados_curso(cursoturma):
    dados = dict(
        curso=services.serialize(cursoturma, add_id=True),
        trabalhadores=[
            services.serialize(matriculacursoturma.trabalhador_educando, add_id=True) for matriculacursoturma in
            cursoturma.matriculacursoturma_set.all()
        ],
        tutores=[
            services.serialize(tutorturma, add_id=True) for tutorturma in cursoturma.turma.tutorturma_set.all()
        ],
    )

    try:
        response = requests.post(
            f'{settings.MOODLE_URL_API}/?sync_up_curso',
            json=json.dumps(dados),
            headers={'Authentication': f'Token {settings.MOODLE_SYNC_TOKEN}'}
        )
        # retorno = json.loads(response.text)
        print(response.text)

    except Exception as e:
        raise BaseException(f"Erro na integração. O Moodle disse: {e}")


def baixar_notas(cursoturma):

    try:
        response = get(f'{settings.MOODLE_URL_API}?sync_down_grades_fesf&nome_breve_curso_moodle={cursoturma.nome_breve_curso_moodle}',
                       headers={'Authentication': f'Token {settings.MOODLE_SYNC_TOKEN}'})
        print(json.loads(response))
        cursoturma.registrar_notas_moodle(json.loads(response))
        retorno = json.loads(response)
    except Exception as e:
        raise BaseException(f"Erro na integração. O Moodle disse: {e}")

    if retorno:
        return retorno
    else:
        raise BaseException(retorno['error'])