import gitlab
import requests
import socket
from django.apps import apps
from django.conf import settings
from urllib.parse import urlparse

from sentry_sdk import capture_exception

from djtools.utils.response import render_to_string

from comum.models import Configuracao
from demandas.models import AnalistaDesenvolvedor
from djtools.utils import get_view_name_from_url


def get_areas():
    # modulos = []
    # for app in apps.get_app_configs():
    #    modulos.append(getattr(app, 'area', 'Administração'))
    # return sorted(list(set(modulos)))
    areas = {
        'administracao': {'area': 'Administração', 'icone': 'tasks'},
        'atividades-estudantis': {'area': 'Atividades Estudantis', 'icone': 'graduation-cap'},
        'comum': {'area': 'Comum', 'icone': 'list'},
        'comunicacao': {'area': 'Comunicação Social', 'icone': 'comment'},
        'desenvolvimento': {'area': 'Desenvolvimento Institucional', 'icone': 'chart-bar'},
        'processos': {'area': 'Documentos e Processos Eletrônicos', 'icone': 'file'},
        'ensino': {'area': 'Ensino', 'icone': 'user-graduate'},
        'extensao': {'area': 'Extensão', 'icone': 'suitcase'},
        'rh': {'area': 'Gestão de Pessoas', 'icone': 'users'},
        'pesquisa': {'area': 'Pesquisa e Inovação', 'icone': 'globe'},
        'ti': {'area': 'Tecnologia da Informação', 'icone': 'laptop'},
    }
    return areas


def get_apps_disponiveis(area=None):
    modulos = []
    for app in apps.get_app_configs():
        if app.label in settings.INSTALLED_APPS_SUAP + ('djtools',):
            if not hasattr(app, 'icon'):
                app.icon = 'list'
            if area:
                if getattr(app, 'area', 'Tecnologia da Informação') == area.get('area'):
                    modulos.append(app)
            else:
                modulos.append(app)
    return sorted(modulos, key=lambda x: (getattr(x, 'area', 'Tecnologia da Informação'), x.verbose_name))


def get_modulo(modulo_id):
    return apps.get_app_config(modulo_id)


def ferramentas_configuradas():
    sentry_token = Configuracao.get_valor_por_chave('comum', 'sentry_token')
    sentry_url = Configuracao.get_valor_por_chave('comum', 'sentry_url')
    gitlab_url = Configuracao.get_valor_por_chave('demandas', 'gitlab_url')
    gitlab_token = Configuracao.get_valor_por_chave('demandas', 'gitlab_token')
    gitlab_suap_id = Configuracao.get_valor_por_chave('demandas', 'gitlab_suap_id')
    if not all([
        sentry_token, sentry_url, gitlab_url, gitlab_token, gitlab_suap_id
    ]):
        return None

    git = gitlab.Gitlab(gitlab_url, private_token=gitlab_token, timeout=60)
    sentry_headers = {'Authorization': f'Bearer {sentry_token}'}

    return {'sentry_url': sentry_url, 'sentry_headers': sentry_headers, 'gitlab_suap_id': gitlab_suap_id, 'git': git}


def get_hostname():
    server_alias = getattr(settings, 'SERVER_ALIAS', '')
    host_name = server_alias and f'{server_alias} - {socket.gethostname()}' or socket.gethostname()

    return host_name


def get_sentry_issue_id_from_url(url):
    try:
        try:
            issue_id = urlparse(url).path.split('/')[-2]
            return int(issue_id)
        except Exception:
            issue_id = urlparse(url).path.split('/')[-1]
            return int(issue_id)
    except Exception:
        return None


def criar_issue_gitlab(erro, conf, request):
    try:
        from erros.models import HistoricoComentarioErro
        descricao_comentario = 'Issue no gitlab criada.'
        HistoricoComentarioErro.objects.create(erro=erro, descricao=descricao_comentario, automatico=True, visibilidade=HistoricoComentarioErro.VISIBILIDADE_ATENDENTES)
        descricao_issue = render_to_string('notificacoes/criar_issue_gitlab.html', {'erro': erro, 'request': request})
        issue = conf['git'].projects.get(conf['gitlab_suap_id']).issues.create({'title': f'Erro {erro.id} - {erro.modulo_afetado_display}', 'description': descricao_issue})
        erro.gitlab_issue_url = issue.web_url
        erro.save()
        return issue.web_url
    except Exception:
        return None


def comentar_erro_issue_gitlab(erro, conf):
    try:
        comentario = f'O erro referente a esta issue está disponível em <a href="{settings.SITE_URL}{erro.get_absolute_url()}">{settings.SITE_URL}{erro.get_absolute_url()}</a>'
        gitlab_issue_id = erro.gitlab_issue_url.split('/')[-1]
        gitlab_issue = conf["git"].projects.get(conf["gitlab_suap_id"]).issues.get(gitlab_issue_id)
        gitlab_issue.discussions.create({'body': comentario})
    except Exception:
        return None


def popular_links_gitlab(erro, conf):
    from erros.models import HistoricoComentarioErro
    try:
        if erro.sentry_issue_id:
            url = f'{conf["sentry_url"]}/api/0/issues/{erro.sentry_issue_id}/'
            if not erro.gitlab_issue_url:
                issues = requests.get(url, headers=conf["sentry_headers"]).json()
                if issues.get('annotations'):
                    html = issues.get('annotations')[0]
                    url = html.split('href="')[1].split('">')[0]
                    erro.gitlab_issue_url = url
                comentar_erro_issue_gitlab(erro, conf)
        if erro.gitlab_issue_url:
            if erro.situacao in [erro.SITUACAO_ABERTO, erro.SITUACAO_REABERTO]:
                erro.situacao = erro.SITUACAO_EM_ANDAMENTO
                descricao = 'Erro colocado em análise automaticamente.'
                HistoricoComentarioErro.objects.create(erro=erro, descricao=descricao, automatico=True)
        erro.save()
        return erro.gitlab_issue_url
    except Exception as e:
        print(e)
    return erro.gitlab_issue_url


def sincronizar_ferramentas(erro, conf, force_close=False):
    from erros.models import HistoricoComentarioErro
    try:
        gitlab_issue_url = popular_links_gitlab(erro, conf)
        if gitlab_issue_url:
            gitlab_issue_id = gitlab_issue_url.split('/')[-1]
            gitlab_issue = conf["git"].projects.get(conf["gitlab_suap_id"]).issues.get(gitlab_issue_id)
            if force_close and gitlab_issue.state == 'opened':
                gitlab_issue.state_event = 'close'
                gitlab_issue.save()
            if gitlab_issue.state == 'closed':
                usuario = None
                if gitlab_issue.assignee:
                    username = gitlab_issue.assignee.get('username', '')
                    desenvolvedor = AnalistaDesenvolvedor.objects.filter(username_gitlab=username).first()
                    if desenvolvedor:
                        usuario = desenvolvedor.usuario
                descricao = 'SUAP atualizado com a correção deste erro.'
                HistoricoComentarioErro.objects.create(erro=erro, descricao=descricao, automatico=True)
                erro.situacao = erro.SITUACAO_RESOLVIDO
                erro.editar_atualizacao(usuario)
                erro.save()
                data = {'status': 'resolved'}
                url = f'{conf["sentry_url"]}/api/0/issues/{erro.sentry_issue_id}/'
                requests.put(url, headers=conf["sentry_headers"], data=data)
    except Exception as e:
        print(e)
        capture_exception(e)


def get_custom_view_name_from_url(url):
    path = urlparse(url).path
    if path.startswith('/erros/modulo/'):
        modulo = path.split('/')[-2]
        return f'{modulo}.views.nao_existe'
    return get_view_name_from_url(url)
