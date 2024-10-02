# -*- coding: utf-8 -*-
import requests
from comum.models import Configuracao

__all__ = ['access_token', 'base_url', 'headers', 'list_branche_names', 'create_pipeline', 'get_job_id', 'execute_job', 'job_log']


def access_token():
    return Configuracao.get_valor_por_chave('demandas', 'gitlab_token', 'GITLAB_API_TOKEN')


def base_url():
    gitlab_url = Configuracao.get_valor_por_chave('demandas', 'gitlab_url', 'GITLAB_URL')
    api_version = Configuracao.get_valor_por_chave('demandas', 'gitlab_api_version', 'GITLAB_API_VERSION')
    project_id = Configuracao.get_valor_por_chave('demandas', 'gitlab_suap_id', 'GITLAB_API_VERSION')
    return '{}/api/v{}/projects/{}'.format(gitlab_url, api_version, project_id)


def headers():
    return {'PRIVATE-TOKEN': access_token()}


def list_branche_names(name=None):
    names = []
    url = '{}/repository/branches?per_page=100'.format(base_url())
    if name:
        url = '{}&search={}'.format(url, name)
    for branch in requests.get(url, headers=headers()).json():
        names.append(branch['name'])
    return names


def create_pipeline(variables, branch='master'):
    requests.get(base_url(), headers=headers()).json()
    data = {'variables': variables}
    url = '{}/pipeline?ref={}'.format(base_url(), branch)
    response = requests.post(url, headers=headers(), json=data).json()
    return response


def get_job_id(pipeline_id, job_name):
    url = '{}/pipelines/{}/jobs'.format(base_url(), pipeline_id)
    jobs = requests.get(url, headers=headers()).json()
    for job in jobs:
        if "name" in job and job['name'] == job_name:
            return job['id']
    return None


def execute_job(pipeline_id, job_name):
    job_id = get_job_id(pipeline_id, job_name)
    url = '{}/jobs/{}'.format(base_url(), job_id)
    job = requests.get(url, headers=headers()).json()
    if "started_at" in job and job['started_at'] is None:
        url = '{}/jobs/{}/play'.format(base_url(), job_id)
        response = requests.post(url, headers=headers()).json()
    else:
        url = '{}/jobs/{}/retry'.format(base_url(), job_id)
        response = requests.post(url, headers=headers()).text
    return response


def job_log(pileline_id, name):
    job_id = get_job_id(pileline_id, name)
    url = '{}/jobs/{}/trace'.format(base_url(), job_id)
    response = requests.get(url, headers=headers()).text
    return response
