import datetime

import gitlab
from requests.exceptions import ConnectTimeout

from comum.models import Comentario, Configuracao
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from djtools.utils import send_notification
from sentry_sdk import capture_exception


def adicionar_comentario(usuario, mensagem, demanda):
    demanda_content = ContentType.objects.get(app_label='demandas', model='demanda')
    comentario = Comentario()
    comentario.cadastrado_por = usuario
    comentario.texto = mensagem
    comentario.content_type = demanda_content
    comentario.content_object = demanda
    comentario.object_id = demanda.id
    comentario.save()


def get_demandantes(demandantes):
    lista = []
    for demandante in demandantes:
        lista.append(demandante.get_profile().nome_usual)
    return ", ".join(lista)


def dados_gerais(demanda):
    texto = '<h3>Dados Gerais</h3>'
    texto += '<dl>'
    texto += f'<dt>Descrição:</dt><dd>{demanda.descricao}</dd>'
    texto += f'<dt>Área de Atuação:</dt><dd>{demanda.area}</dd>'
    if demanda.prioridade:
        texto += f'<dt>Prioridade para Desenvolvimento:</dt><dd>{demanda.prioridade}</dd>'
    texto += f'<dt>Demandantes:</dt><dd>{get_demandantes(demanda.demandantes.all())}</dd>'
    texto += '<dt>Criada em:</dt><dd>{}</dd>'.format(demanda.aberto_em.strftime("%d/%m/%Y %H:%M"))
    texto += '</dl>'
    texto += '<p>--</p>'
    texto += '<p>Para mais informações, acesse: <a href="{0!s}">{0!s}</a></p>'.format(demanda.get_visualizar_demanda_url())
    return texto


class Notificar:
    @staticmethod
    def demanda_aberta(demanda):
        titulo = '[SUAP] Nova Demanda'
        texto = []
        texto.append('<h1>Nova Demanda</h1>')
        texto.append(f'<h2>#{demanda.pk} {demanda.titulo}</h2>')
        texto.append(f'<p>{demanda.descricao}</p>')
        texto.append('<h3>Dados Gerais</h3>')
        texto.append('<dl>')
        texto.append(f'<dt>Demandantes:</dt><dd>{get_demandantes(demanda.demandantes.all())}</dd>')
        texto.append('<dt>Criada em:</dt><dd>{}</dd>'.format(demanda.aberto_em.strftime("%d/%m/%Y %H:%M")))
        texto.append('</dl>')
        texto.append('<p>--</p>')
        texto.append('<p>Para mais informações, acesse: <a href="{0!s}">{0!s}</a></p>'.format(demanda.get_visualizar_demanda_url()))
        vinculos = set().union(demanda.get_vinculos_recebedores_novas_demandas(), demanda.get_vinculos_interessados())
        send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, vinculos, objeto=demanda)

    @staticmethod
    def alteracao_demanda(demanda):
        titulo = f'[SUAP] Atualização de Demanda #{demanda.pk}'
        texto = []
        texto.append('<h1>Atualização da Descrição da Demanda</h1>')
        texto.append(f'<h2>#{demanda.pk} {demanda.titulo}</h2>')
        texto.append('<h3>Novo Conteúdo</h3>')
        texto.append(f'<p>{demanda.descricao}</p>')
        texto.append('<h3>Dados Gerais</h3>')
        texto.append('<dl>')
        texto.append(f'<dt>Demandantes:</dt><dd>{get_demandantes(demanda.demandantes.all())}</dd>')
        if demanda.prioridade:
            texto.append(f'<dt>Prioridade para Desenvolvimento:</dt><dd>{demanda.prioridade}</dd>')
        texto.append('<dt>Criada em:</dt><dd>{}</dd>'.format(demanda.aberto_em.strftime("%d/%m/%Y %H:%M")))
        texto.append('</dl>')
        texto.append('<p>--</p>')
        texto.append('<p>Para mais informações, acesse: <a href="{0!s}">{0!s}</a></p>'.format(demanda.get_visualizar_demanda_url()))
        responsaveis = demanda.get_vinculos_analistas() or demanda.get_vinculos_recebedores_novas_demandas()
        vinculos = set().union(responsaveis, demanda.get_vinculos_interessados())
        send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, vinculos, categoria='Atualização de Demanda', objeto=demanda)

    @staticmethod
    def situacao_alterada(demanda, texto_comentario=None, estado_em_analise=False, estado_em_homologacao=False, eh_observador=False):
        ultimo_historico_situacao = demanda.get_ultimo_historico_situacao()
        titulo = f'[SUAP] Demanda #{demanda.pk}: Alteração de Etapa'
        texto = []
        texto.append('<h1>Alteração de Etapa da Demanda</h1>')
        texto.append(f'<h2>#{demanda.pk} {demanda.titulo}</h2>')
        texto.append(f'<p>Etapa alterada para <strong>{ultimo_historico_situacao.situacao}</strong>; atualização realizada por {ultimo_historico_situacao.usuario}.</p>')
        if not eh_observador:
            if estado_em_analise:
                texto.append("<p>A consolidação da demanda foi liberada para avaliação.</p>")
                texto.append("<p>Você deve acessar a demanda, acessar a aba 'Consolidação' e revisar o conteúdo.</p>")
                texto.append("<p>Caso você seja o Demandante, você deve, após revisão do conteúdo, selecionar uma das opções: Aprovar ou Reprovar.</p>")
            if estado_em_homologacao:
                texto.append("<p>A demanda foi liberada para homologação.</p>")
                texto.append("<p>Você deve acessar a demanda, acessar a aba 'Homologação' e acessar a URL para Homologação da demanda.</p>")
                texto.append("<p>No Ambiente de Homologação, você deve <strong>testar todas as regras</strong> definidas na consolidação da demanda.</p>")
                texto.append("<p>Caso você seja o Demandante, você deve, após realização de testes, selecionar uma das opções: Aprovar ou Reprovar.</p>")
            if texto_comentario or ultimo_historico_situacao.data_previsao or ultimo_historico_situacao.data_conclusao:
                texto.append('<h3>Dados da Atualização</h3>')
                texto.append('<dl>')
                if texto_comentario:
                    texto.append(f'<dt>Comentário:</dt><dd>{texto_comentario}</dd>')
                if ultimo_historico_situacao.data_previsao:
                    texto.append('<dt>Data de previsão para conclusão desta etapa:</dt><dd>{}</dd>'.format(ultimo_historico_situacao.data_previsao.strftime("%d/%m/%Y")))
                if ultimo_historico_situacao.data_conclusao:
                    texto.append('<dt>Data de conclusão da etapa anterior:</dt><dd>{}</dd>'.format(ultimo_historico_situacao.data_conclusao.strftime("%d/%m/%Y")))
                texto.append('</dl>')
        texto.append(dados_gerais(demanda))
        if demanda.get_vinculos_analistas() or demanda.get_vinculos_desenvolvedores():
            responsaveis = set().union(demanda.get_vinculos_analistas(), demanda.get_vinculos_desenvolvedores())
        else:
            responsaveis = demanda.get_vinculos_recebedores_novas_demandas()
        vinculos = set().union(responsaveis, demanda.get_vinculos_interessados(), demanda.get_vinculos_observadores())
        if ultimo_historico_situacao.usuario:
            vinculos.discard(ultimo_historico_situacao.usuario.get_vinculo())
        send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, vinculos, categoria='Demanda: Alteração de Etapa', objeto=demanda)

    @staticmethod
    def nota_interna_criada(nota_interna):
        demanda = nota_interna.demanda
        titulo = f'[SUAP] Demanda #{demanda.pk}: Nova Nota Interna'
        texto = []
        texto.append('<h1>Nova Nota Interna</h1>')
        texto.append(f'<h2>#{demanda.pk} {demanda.titulo}</h2>')
        texto.append('<p>Uma nova nota interna foi adicionada à esta demanda.</p>')
        texto.append('<h3>Dados Gerais</h3>')
        texto.append('<dl>')
        texto.append(f'<dt>Descrição:</dt><dd>{demanda.descricao}</dd>')
        if demanda.prioridade:
            texto.append(f'<dt>Prioridade para Desenvolvimento:</dt><dd>{demanda.prioridade}</dd>')
        texto.append(f'<dt>Demandantes:</dt><dd>{get_demandantes(demanda.demandantes.all())}</dd>')
        texto.append('<dt>Criada em:</dt><dd>{}</dd>'.format(demanda.aberto_em.strftime("%d/%m/%Y %H:%M")))
        texto.append('</dl>')
        texto.append('<p>--</p>')
        texto.append('<p>Para mais informações, acesse: <a href="{0!s}?tab=nota_interna">{0!s}?tab=nota_interna</a></p>'.format(demanda.get_visualizar_demanda_url()))
        vinculos = set().union(demanda.get_vinculos_analistas(), demanda.get_vinculos_desenvolvedores())
        vinculos = [vinculo for vinculo in vinculos if vinculo != nota_interna.usuario.get_vinculo()]
        if vinculos:
            send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, vinculos, categoria='Demanda: Nova Nota Interna', objeto=demanda)

    @staticmethod
    def novo_comentario(comentario):
        demanda = comentario.content_object
        usuario = comentario.cadastrado_por.get_profile().nome_usual
        texto = []
        if comentario.texto:
            titulo = f'[SUAP] Demanda #{demanda.pk}: Novo Comentário'
            texto.append('<h1>Novo Comentário</h1>')
        else:
            titulo = f'[SUAP] Demanda #{demanda.pk}: Novo Anexo'
            texto.append('<h1>Novo Anexo</h1>')
        texto.append(f'<h2>#{demanda.pk} {demanda.titulo}</h2>')
        if comentario.texto:
            texto.append('<dl>')
            texto.append(f'<dt>Comentário por {usuario}:</dt><dd>{comentario.texto}</dd>')
            if comentario.resposta:
                texto.append(f'<dt>Em resposta ao comentário de {comentario.resposta.cadastrado_por.get_profile().nome_usual}:</dt><dd>{comentario.resposta.texto}</dd>')
        else:
            texto.append('<dl>')
            texto.append(f'<dt>Arquivo anexado por {usuario}:</dt><dd>Para visualizar o anexo, acesse o link abaixo e clique em Anexos.</dd>')
        texto.append('</dl>')
        texto.append('<h3>Dados Gerais</h3>')
        texto.append('<dl>')
        texto.append(f'<dt>Descrição:</dt><dd>{demanda.descricao}</dd>')
        if demanda.prioridade:
            texto.append(f'<dt>Prioridade para Desenvolvimento:</dt><dd>{demanda.prioridade}</dd>')
        texto.append(f'<dt>Demandantes:</dt><dd>{get_demandantes(demanda.demandantes.all())}</dd>')
        texto.append('<dt>Criada em:</dt><dd>{}</dd>'.format(demanda.aberto_em.strftime("%d/%m/%Y %H:%M")))
        texto.append('</dl>')
        texto.append('<p>--</p>')
        texto.append('<p>Para mais informações, acesse: <a href="{0!s}?tab=linha_tempo">{0!s}?tab=linha_tempo</a></p>'.format(demanda.get_visualizar_demanda_url()))
        if demanda.get_vinculos_analistas() or demanda.get_vinculos_desenvolvedores():
            responsaveis = set().union(demanda.get_vinculos_analistas(), demanda.get_vinculos_desenvolvedores())
        else:
            responsaveis = demanda.get_vinculos_recebedores_novas_demandas()
        vinculos = set().union(responsaveis, demanda.get_vinculos_interessados())
        if comentario.cadastrado_por:
            vinculos.discard(comentario.cadastrado_por.get_vinculo())
        send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, vinculos, categoria='Demanda: Novo Comentário', objeto=demanda)

    @staticmethod
    def desenvolvedores_vinculados_a_demanda(demanda, novos_desenvolvedores, vinculado_por):
        titulo = f'[SUAP] Vinculação à Demanda #{demanda.pk}'
        categoria = 'Vinculação à Demanda'
        texto = []
        texto.append(f'<h1>{categoria}</h1>')
        texto.append(f'<h2>#{demanda.pk} {demanda.titulo}</h2>')
        texto.append('<p>Você foi vinculado a esta demanda como <strong>Desenvolvedor</strong>.</p>')
        texto.append(dados_gerais(demanda))
        desenvolvedores = [desenvolvedor.get_vinculo() for desenvolvedor in novos_desenvolvedores if desenvolvedor != vinculado_por]
        if desenvolvedores:
            send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, desenvolvedores, categoria=categoria, objeto=demanda)

    @staticmethod
    def analistas_vinculados_a_demanda(demanda, novos_analistas, vinculado_por):
        titulo = f'[SUAP] Vinculação à Demanda #{demanda.pk}'
        texto = []
        texto.append('<h1>Vinculação à Demanda</h1>')
        texto.append(f'<h2>#{demanda.pk} {demanda.titulo}</h2>')
        texto.append('<p>Você foi vinculado a esta demanda como <strong>Analista</strong>.</p>')
        texto.append(dados_gerais(demanda))
        if novos_analistas:
            for analista in novos_analistas:
                if analista != vinculado_por:
                    send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [analista.get_vinculo()], categoria='Vinculação à Demanda', objeto=demanda)

    @staticmethod
    def solicitacao_observador(demanda):
        titulo = f'[SUAP] Solicitação de Acompanhamento da Demanda #{demanda.pk}'
        categoria = 'Solicitação de Acompanhamento da Demanda'
        texto = []
        texto.append(f'<h1>{categoria}</h1>')
        texto.append(f'<h2>#{demanda.pk} {demanda.titulo}</h2>')
        texto.append('<p>Um usuário solicitou acompanhamento desta demanda como <strong>Observador</strong>.</p>')
        texto.append(dados_gerais(demanda))
        send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, demanda.get_vinculos_demandantes(), categoria=categoria, objeto=demanda)

    @staticmethod
    def adicao_como_observador(demanda, user):
        titulo = f'[SUAP] Vinculação à Demanda #{demanda.pk}'
        categoria = 'Vinculação à Demanda'
        texto = []
        texto.append(f'<h1>{categoria}</h1>')
        texto.append(f'<h2>#{demanda.pk} {demanda.titulo}</h2>')
        texto.append('<p>Você foi vinculado a esta demanda como <strong>Observador</strong>.</p>')
        texto.append(dados_gerais(demanda))

        send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [user.get_vinculo()], categoria=categoria, objeto=demanda)

    @staticmethod
    def remocao_como_observador_pendente(demanda, user):
        titulo = f'[SUAP] Solicitação de Acompanhamento da Demanda #{demanda.pk}'
        categoria = 'Solicitação de Acompanhamento da Demanda'
        texto = []
        texto.append(f'<h1>{categoria}</h1>')
        texto.append(f'<h2>#{demanda.pk} {demanda.titulo}</h2>')
        texto.append('<p>Sua solicitação de acompanhamento a esta demanda como Observador foi <strong>negada</strong> pelos demandantes.</p>')
        texto.append(dados_gerais(demanda))

        send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [user.get_vinculo()], categoria=categoria, objeto=demanda)

    @staticmethod
    def nova_sugestao_melhoria(sugestao_melhoria):
        # notifica os demandantes da área de atuação da sugestão
        vinculos_users_to = set().union(
            [_.get_vinculo() for _ in sugestao_melhoria.area_atuacao.demandantes.all()],
            [_.get_vinculo() for _ in [sugestao_melhoria.area_atuacao.demandante_responsavel] if _]
        )

        titulo = '[SUAP] Nova Sugestão de Melhoria na sua Área de Atuação'
        url = f'{settings.SITE_URL}{sugestao_melhoria.get_absolute_url()}'

        texto = [
            '<h1>Sugestão de Melhoria</h1>',
            f'<h2>{sugestao_melhoria.titulo}</h2>',
            '<dl>',
            f'<dt>Descrição:</dt><dd>{sugestao_melhoria.descricao}</dd>',
            f'<dt>Requisitante:</dt><dd>{sugestao_melhoria.requisitante.get_vinculo()}</dd>',
            '</dl>',
            '<p>--</p>',
            f'<p>Para mais informações, acesse: <a href="{url}">{url}</a></p>'
        ]

        send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL,
                          vinculos_users_to, categoria='Sugestão de Melhoria: Nova Sugestão', objeto=sugestao_melhoria)

    @staticmethod
    def nova_situacao_em_sugestao_melhoria(sugestao_melhoria, user_editor):
        # notifica o requisitante, os interessados e o responsável da sugestão, exceto quem fez a edição
        vinculos_users_to = set().union(
            [sugestao_melhoria.requisitante.get_vinculo()],
            [_.get_vinculo() for _ in sugestao_melhoria.interessados.all()],
            [_.get_vinculo() for _ in [sugestao_melhoria.responsavel] if _]
        )
        vinculos_users_to.discard(user_editor.get_vinculo())

        titulo = f'[SUAP] Sugestão de Melhoria #{sugestao_melhoria.pk}: Nova Situação'
        url = f'{settings.SITE_URL}{sugestao_melhoria.get_absolute_url()}'

        texto = [
            '<h1>Sugestão de Melhoria</h1>',
            f'<h2>{sugestao_melhoria.titulo}</h2>',
            '<dl>',
            f'<dt>Situação alterada para:</dt><dd>{sugestao_melhoria.get_situacao_display()}</dd>',
            f'<dt>Alteração feita por:</dt><dd>{user_editor.get_vinculo()}</dd>',
            '</dl>',
            '<p>--</p>',
            f'<p>Para mais informações, acesse: <a href="{url}">{url}</a></p>'
        ]

        send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL,
                          vinculos_users_to, categoria='Sugestão de Melhoria: Nova Situação', objeto=sugestao_melhoria)

    @staticmethod
    def novo_comentario_em_sugestao_melhoria(sugestao_melhoria, comentario):
        if not comentario.content_object == sugestao_melhoria:
            raise Exception('O comentário não pode ser notificado nesta sugestão de melhoria.')

        # notifica o requisitante, os interessados e o responsável da sugestão, exceto quem fez o comentário
        vinculos_users_to = set().union(
            [sugestao_melhoria.requisitante.get_vinculo()],
            [_.get_vinculo() for _ in sugestao_melhoria.interessados.all()],
            [_.get_vinculo() for _ in [sugestao_melhoria.responsavel] if _]
        )
        vinculos_users_to.discard(comentario.cadastrado_por.get_vinculo())

        titulo = f'[SUAP] Sugestão de Melhoria #{sugestao_melhoria.pk}: Novo Comentário'
        url = f'{settings.SITE_URL}{sugestao_melhoria.get_absolute_url()}'

        texto = [
            '<h1>Sugestão de Melhoria</h1>',
            f'<h2>{sugestao_melhoria.titulo}</h2>',
            '<dl>',
            f'<dt>Comentário:</dt><dd>{comentario.texto}</dd>',
            '<dt>Comentário feito por:</dt><dd>{}</dd>'.format(
                comentario.cadastrado_por.get_profile().nome_usual)
        ]

        if comentario.resposta:
            texto.append('<dt>Em resposta ao comentário de {}:</dt><dd>{}</dd>'.format(
                comentario.resposta.cadastrado_por.get_profile().nome_usual,
                comentario.resposta.texto))

        texto.append('</dl>')
        texto.append('<p>--</p>')
        texto.append('<p>Para mais informações, acesse: <a href="{0!s}">{0!s}</a></p>'.format(url))

        send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL,
                          vinculos_users_to, categoria='Sugestão de Melhoria: Novo Comentário', objeto=sugestao_melhoria)

    @staticmethod
    def ambiente_homologacao_expira_em_1_dia(ambiente):
        titulo = f'[SUAP] Ambiente de Homologação #{ambiente.branch}: Aviso de Expiração e Remoção'

        categoria = 'Ambientes de Homologação - SUAPDevs'
        texto = []
        texto.append(f'<h1>{categoria}</h1>')
        texto.append(f'<h2>#{ambiente.pk} {ambiente.branch}</h2>')
        texto.append(f'<p>Seu ambiente referente a branch {ambiente.branch} irá expirar em {ambiente.data_expiracao.strftime("%d/%m/%Y")} e será removido definitivamente.</p>')
        texto.append('<p>Atualize a data de expiração se necessário para manter o ambiente ativo.</p>')
        texto.append('<h3>Dados Gerais</h3>')
        texto.append('<dl>')
        texto.append(f'<dt>Branch:</dt><dd>{ambiente.branch}</dd>')
        texto.append(f'<dt>Url gitlab:</dt><dd>{ambiente.url_gitlab}</dd>')
        texto.append('<dt>Criado em:</dt><dd>{}</dd>'.format(ambiente.data_criacao.strftime("%d/%m/%Y")))
        texto.append('</dl>')
        texto.append('<p>--</p>')
        url = f'{settings.SITE_URL}{ambiente.get_absolute_url()}'
        texto.append('<p>Para mais informações, acesse: <a href="{0!s}">{0!s}</a></p>'.format(url))

        send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [ambiente.criador.usuario.get_vinculo()], categoria=categoria, objeto=ambiente)


def sincronizar_demandas_atualizacoes(demanda):
    gitlab_url = Configuracao.get_valor_por_chave('demandas', 'gitlab_url')
    gitlab_token = Configuracao.get_valor_por_chave('demandas', 'gitlab_token')
    gitlab_suap_id = Configuracao.get_valor_por_chave('demandas', 'gitlab_suap_id')
    if not all([
        gitlab_url, gitlab_token, gitlab_suap_id
    ]):
        return 'Gitlab não está configurado no SUAP.'
    try:
        from demandas.models import (AnalistaDesenvolvedor,
                                     Situacao)

        git = gitlab.Gitlab(gitlab_url, private_token=gitlab_token, timeout=60)
        merge_request = git.projects.get(gitlab_suap_id).mergerequests.get(demanda.id_merge_request)
        if merge_request.state == 'merged':
            analista_mr = AnalistaDesenvolvedor.objects.filter(username_gitlab=merge_request.merged_by['username']).first()
            hoje = datetime.date.today()
            demanda.alterar_situacao(analista_mr.usuario, Situacao.ESTADO_CONCLUIDO, data_conclusao=hoje)
    except ConnectTimeout:
        print('Gitlab indisponível.')
    except Exception as e:
        capture_exception(e)
