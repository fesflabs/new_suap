from django.conf import settings
from django.template import Template, Context

from djtools.utils import send_notification


class Notificar:
    @staticmethod
    def chamado_aberto(chamado, enviar_copia_email):
        """ Enviando email, notificando abertura do chamado """
        titulo = '[SUAP] Central de Serviços: Novo Chamado'
        texto = []
        texto.append('<h1>Novo Chamado</h1>')
        texto.append('<h2>#{} {}</h2>'.format(chamado.pk, chamado.servico.nome))
        texto.append('<dl>')
        template = Template('<dt>Descrição do Chamado:</dt><dd>{{descricao}}</dd>').render(Context({'descricao': chamado.descricao}))
        texto.append(template)
        texto.append('<dt>Interessado Principal:</dt><dd>{}</dd>'.format(chamado.interessado.get_profile().nome_usual))
        texto.append('<dt>Aberto em:</dt><dd>{}</dd>'.format(chamado.aberto_em.strftime("%d/%m/%Y %H:%M")))
        texto.append('<dt>Data de Estouro do SLA:</dt><dd>{}</dd>'.format(chamado.data_limite_atendimento.strftime("%d/%m/%Y %H:%M")))
        texto.append('</dl>')
        texto.append('<p>--</p>')
        texto.append('<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(chamado.get_visualizar_chamado_url()))
        if enviar_copia_email:
            send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, chamado.get_vinculos_interessados(), objeto=chamado)
        if chamado.get_atendimento_atribuicao_atual().grupo_atendimento:
            send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, chamado.get_atendimento_atribuicao_atual().grupo_atendimento.get_vinculos_responsaveis(), objeto=chamado)

    @staticmethod
    def chamado_atribuido(chamado):
        """ Enviando email, notificando atribuição de chamado """
        titulo = '[SUAP] Central de Serviços: Chamado #{} atribuído a você'.format(chamado.pk)
        texto = []
        texto.append('<h1>Chamado atribuído a você</h1>')
        texto.append('<h2>#{} {}</h2>'.format(chamado.pk, chamado.servico.nome))
        texto.append('<dl>')
        template = Template('<dt>Descrição do Chamado:</dt><dd>{{descricao}}</dd>').render(Context({'descricao': chamado.descricao}))
        texto.append(template)
        texto.append('<dt>Interessado Principal:</dt><dd>{}</dd>'.format(chamado.interessado.get_profile().nome_usual))
        texto.append('<dt>Aberto em:</dt><dd>{}</dd>'.format(chamado.aberto_em.strftime("%d/%m/%Y %H:%M")))
        texto.append('<dt>Data de Estouro do SLA:</dt><dd>{}</dd>'.format(chamado.data_limite_atendimento.strftime("%d/%m/%Y %H:%M")))
        texto.append('</dl>')
        texto.append('<p>--</p>')
        texto.append('<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(chamado.get_visualizar_chamado_url()))
        atribuido_para = chamado.get_atendimento_atribuicao_atual().atribuido_para
        if atribuido_para:
            send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [atribuido_para.get_vinculo()], categoria='Central de Serviços: Chamado atribuído a você', objeto=chamado)

    @staticmethod
    def adicao_outros_interessados(chamado, outros_interessados):
        """ Enviando email, notificado que outras pessoas foram adicionadas como interessados no chamado. """
        titulo = '[SUAP] Chamado #{}: Novos Interessados'.format(chamado.pk)
        texto = []
        outros_interessados_nomes = ", ".join([item.get_profile().nome_usual for item in outros_interessados])
        texto.append('<h1>Novos Interessados</h1>')
        texto.append('<h2>#{} {}</h2>'.format(chamado.pk, chamado.servico.nome))
        texto.append('<dl>')
        texto.append('<dt>Outros Interessados:</dt><dd>{}</dd>'.format(outros_interessados_nomes))
        texto.append('</dl>')
        texto.append('<h3>Dados Gerais</h3>')
        texto.append('<dl>')
        template = Template('<dt>Descrição do Chamado:</dt><dd>{{descricao}}</dd>').render(Context({'descricao': chamado.descricao}))
        texto.append(template)
        texto.append('<dt>Interessado Principal:</dt><dd>{}</dd>'.format(chamado.interessado.get_profile().nome_usual))
        texto.append('<dt>Aberto em:</dt><dd>{}</dd>'.format(chamado.aberto_em.strftime("%d/%m/%Y %H:%M")))
        texto.append('</dl>')
        texto.append('<p>--</p>')
        texto.append('<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(chamado.get_visualizar_chamado_url()))
        if outros_interessados:
            outros_interessados_por_vinculo = []
            for interessado in outros_interessados:
                outros_interessados_por_vinculo.append(interessado.get_vinculo())
            send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, outros_interessados_por_vinculo, categoria='Chamado: Novos Interessados', objeto=chamado)

    @staticmethod
    def adicao_anexo(anexo):
        """ Enviando email, notificado que arquivos foram anexados ao chamado. """
        titulo = '[SUAP] Chamado #{}: Novo Anexo'.format(anexo.chamado_id)
        texto = []
        texto.append('<h1>Novos Anexo</h1>')
        texto.append('<h2>#{} {}</h2>'.format(anexo.chamado_id, anexo.chamado.servico.nome))
        texto.append('<dl>')
        texto.append('<dt>Descrição do arquivo anexado:</dt><dd>{}</dd>'.format(anexo.descricao))
        texto.append('<dt>Anexado por:</dt><dd>{}</dd>'.format(anexo.anexado_por.get_profile().nome_usual))
        texto.append('</dl>')
        texto.append('<h3>Dados Gerais</h3>')
        texto.append('<dl>')
        template = Template('<dt>Descrição do Chamado:</dt><dd>{{descricao}}</dd>').render(Context({'descricao': anexo.chamado.descricao}))
        texto.append(template)
        texto.append('<dt>Interessado Principal:</dt><dd>{}</dd>'.format(anexo.chamado.interessado.get_profile().nome_usual))
        texto.append('<dt>Aberto em:</dt><dd>{}</dd>'.format(anexo.chamado.aberto_em.strftime("%d/%m/%Y %H:%M")))
        texto.append('</dl>')
        texto.append('<p>--</p>')
        texto.append('<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(anexo.chamado.get_visualizar_chamado_url()))
        if anexo.anexado_por == anexo.chamado.interessado or anexo.chamado.eh_outro_interessado(anexo.anexado_por):
            atribuido_para = anexo.chamado.get_atendimento_atribuicao_atual().atribuido_para
            if atribuido_para:
                send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [atribuido_para.get_vinculo()], categoria='Chamado: Novo Anexo', objeto=anexo.chamado)

    @staticmethod
    def comentario(comunicacao):
        titulo = '[SUAP] Chamado #{}: Novo Comentário'.format(comunicacao.chamado_id)
        texto = []
        atribuido_para = comunicacao.chamado.get_atendimento_atribuicao_atual().atribuido_para
        texto.append('<h1>Novo Comentário</h1>')
        texto.append('<h2>#{} {}</h2>'.format(comunicacao.chamado_id, comunicacao.chamado.servico.nome))
        texto.append('<dl>')
        texto.append('<dt>Comentário por {}:</dt><dd>{}</dd>'.format(comunicacao.remetente.get_profile().nome_usual, comunicacao.texto))
        texto.append('</dl>')
        texto.append('<h3>Dados Gerais</h3>')
        texto.append('<dl>')
        template = Template('<dt>Descrição do Chamado:</dt><dd>{{descricao}}</dd>').render(Context({'descricao': comunicacao.chamado.descricao}))
        texto.append(template)
        if atribuido_para:
            texto.append('<dt>Atendente:</dt><dd>{}</dd>'.format(atribuido_para.get_profile().nome_usual))
        texto.append('</dl>')
        texto.append('<p>--</p>')
        texto.append('<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(comunicacao.chamado.get_visualizar_chamado_url()))

        remetente = comunicacao.remetente.get_vinculo()
        destinatarios_email = comunicacao.chamado.get_vinculos_interessados()
        if atribuido_para:
            destinatarios_email.append(atribuido_para.get_vinculo())
        if remetente in destinatarios_email:
            destinatarios_email.remove(remetente)
        send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, destinatarios_email, categoria='Chamado: Novo Comentário', objeto=comunicacao.chamado)

    @staticmethod
    def nota_interna_ao_atendente(comunicacao, citar_outros_usuarios=None):
        """ Enviando email, quando nota interna for registrada """
        titulo = '[SUAP] Chamado #{}: Nova Nota Interna'.format(comunicacao.chamado_id)
        texto = []
        texto.append('<h1>Nova Nota Interna</h1>')
        texto.append('<h2>#{} {}</h2>'.format(comunicacao.chamado_id, comunicacao.chamado.servico.nome))
        texto.append('<dl>')
        texto.append('<dt>Nota Interna por {}:</dt><dd>{}</dd>'.format(comunicacao.remetente.get_profile().nome_usual, comunicacao.texto))
        texto.append('</dl>')
        texto.append('<h3>Dados Gerais</h3>')
        texto.append('<dl>')
        template = Template('<dt>Descrição do Chamado:</dt><dd>{{descricao}}</dd>').render(Context({'descricao': comunicacao.chamado.descricao}))
        texto.append(template)
        texto.append('<dt>Atendente:</dt><dd>{}</dd>'.format(comunicacao.remetente.get_profile().nome_usual))
        texto.append('</dl>')
        texto.append('<p>--</p>')
        texto.append('<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(comunicacao.chamado.get_visualizar_chamado_url()))
        if citar_outros_usuarios:
            vinculos_citados = []
            for usuario in comunicacao.usuarios_citados.all():
                vinculos_citados.append(usuario.get_vinculo())
            send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, vinculos_citados, categoria='Chamado: Nova Nota Interna', objeto=comunicacao.chamado)
        else:
            atribuido_para = comunicacao.chamado.get_atendimento_atribuicao_atual().atribuido_para
            if atribuido_para and comunicacao.remetente != atribuido_para:
                send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [atribuido_para.get_vinculo()], categoria='Chamado: Nova Nota Interna', objeto=comunicacao.chamado)

    @staticmethod
    def status_atualizado(chamado):
        """ Enviando email, notificando alteração de status para usuário
            e para chefe do grupo de atendimento (quando resolvido = True) """
        from centralservicos.models import StatusChamado

        status = StatusChamado.STATUS[chamado.status]
        historico_status = chamado.get_ultimo_historico_status()
        titulo = '[SUAP] Central de Serviços: Chamado {}'.format(status)
        texto = []
        alterado_por = chamado.get_ultimo_historico_status().usuario
        texto.append('<h1>Chamado {}</h1>'.format(status))
        texto.append('<h2>#{} {}</h2>'.format(chamado.pk, chamado.servico.nome))
        texto.append('<dl>')
        texto.append('<dt>Atualização de chamado realizada por {}:</dt><dd>Situação alterada para <strong>{}</strong>.</dd>'.format(alterado_por, status))
        if historico_status.comunicacao:
            texto.append('<dt>Comentário por {}:</dt><dd>{}</dd>'.format(historico_status.comunicacao.remetente.get_profile().nome_usual, historico_status.comunicacao.texto))
        texto.append('</dl>')
        texto.append('<h3>Dados Gerais</h3>')
        texto.append('<dl>')
        template = Template('<dt>Descrição do Chamado:</dt><dd>{{descricao}}</dd>').render(Context({'descricao': chamado.descricao}))
        texto.append(template)
        texto.append('<dt>Interessado Principal:</dt><dd>{}</dd>'.format(chamado.interessado.get_profile().nome_usual))
        texto.append('<dt>Aberto em:</dt><dd>{}</dd>'.format(chamado.aberto_em.strftime("%d/%m/%Y %H:%M")))
        texto.append('<dt>Data de Estouro do SLA:</dt><dd>{}</dd>'.format(chamado.data_limite_atendimento.strftime("%d/%m/%Y %H:%M")))
        texto.append('</dl>')
        texto.append('<p>--</p>')
        texto.append('<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(chamado.get_visualizar_chamado_url()))

        atribuido_para = chamado.get_atendimento_atribuicao_atual().atribuido_para
        if chamado.status == StatusChamado.get_status_resolvido():
            texto.append(' | Se o chamado foi resolvido a contento, por favor mude a situação do ' 'chamado para "FECHADO".')
            responsaveis = chamado.get_atendimento_atribuicao_atual().grupo_atendimento.get_vinculos_responsaveis()
            responsaveis = [responsavel for responsavel in responsaveis if responsavel != alterado_por.get_vinculo()]
            if responsaveis:
                send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, responsaveis, objeto=chamado)
            if chamado.interessado:
                send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, chamado.get_vinculos_interessados(), objeto=chamado)
        elif chamado.status == StatusChamado.get_status_reaberto():
            if atribuido_para and alterado_por != atribuido_para:
                send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [atribuido_para.get_vinculo()], objeto=chamado)
        elif chamado.status == StatusChamado.get_status_fechado():
            # quem alterou nao foi o interessado
            if not (historico_status.usuario == chamado.interessado) and chamado.interessado:
                send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, chamado.get_vinculos_interessados(), objeto=chamado)
            else:
                if chamado.nota_avaliacao:
                    texto.insert(-3, '<dt>Nota da Avaliação:</dt><dd>{}</dd>'.format(chamado.nota_avaliacao))
                if chamado.comentario_avaliacao:
                    texto.insert(-3, '<dt>Comentário da Avaliação:</dt><dd>{}</dd>'.format(chamado.comentario_avaliacao))

                send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [atribuido_para.get_vinculo()], objeto=chamado)
        else:
            if chamado.interessado:
                send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, chamado.get_vinculos_interessados(), objeto=chamado)

    @staticmethod
    def chamados_resolvidos(interessado, chamados):
        """ Enviando email, notificando ao interessado que seus chamados
            foram resolvidos e devem ser fechados """
        titulo = '[SUAP] Central de Serviços: Chamados Resolvidos'
        texto = []
        texto.append('<h1>Chamados Resolvidos</h1>')
        if len(chamados) == 1:
            texto.append('<p>Você abriu o seguinte chamado na Central de Serviços do SUAP que foi resolvido, mas que deve ser fechado:</p>')
        else:
            texto.append('<p>Você abriu os seguintes chamados na Central de Serviços do SUAP que foram resolvidos, mas que devem ser fechados:</p>')
        texto.append('<ol>')
        for chamado in chamados:
            texto.append('<li>#{} - {}</li>'.format(chamado.pk, chamado.servico.nome))
        texto.append('</ol>')
        texto.append(
            '<p>Para fechar um chamado, acesse <a href="{0}/centralservicos/meus_chamados/?status=3">{0}/centralservicos/meus_chamados/?status=3</a> '
            'e clique em "Fechar chamado".</p>'.format(settings.SITE_URL)
        )
        if interessado:
            send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [interessado.get_vinculo()], fail_silently=False)

    @staticmethod
    def supervisao_pendente_em_base_conhecimento(baseconhecimento, supervisores):
        titulo = '[SUAP] Central de Serviços: Base de Conhecimento Pendente de Supervisão'
        texto = []
        texto.append('<h1>Central de Serviços</h1>')
        texto.append('<h2>Base de Conhecimento Pendente de Supervisão</h2>')
        texto.append(
            '<p>A Base de Conhecimento #{} ({}) foi atualizada e necessita de sua aprovação para ficar disponível aos atendentes da Central de Serviços.</p>'.format(
                baseconhecimento.pk, baseconhecimento.titulo
            )
        )
        texto.append('<dl>')
        texto.append('<dt>Resumo da Base de Conhecimento:</dt><dd>{}</dd>'.format(baseconhecimento.resumo))
        texto.append('<dt>Atualizado por:</dt><dd>{}</dd>'.format(baseconhecimento.atualizado_por.get_profile().nome_usual))
        texto.append('</dl>')
        texto.append('<p>--</p>')
        texto.append('<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(baseconhecimento.get_visualizar_base_conhecimento_url()))
        if supervisores:
            supervisores_por_vinculos = []
            for usuario in supervisores:
                supervisores_por_vinculos.append(usuario.get_vinculo())
            send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, supervisores_por_vinculos, objeto=baseconhecimento)

    @staticmethod
    def base_conhecimento_marcada_para_revisao(baseconhecimento, comentario, usuario):
        titulo = '[SUAP] Central de Serviços: Base de Conhecimento Marcada para Correção'
        texto = []
        texto.append('<h1>Central de Serviços</h1>')
        texto.append('<h2>Base de Conhecimento Marcada para Correção</h2>')
        texto.append(
            '<p>A Base de Conhecimento #{} ({}) foi marcada para correção. Você deve acessar a Central de Serviços e verificar as informações contidas na Base de Conhecimento.</p>'.format(
                baseconhecimento.pk, baseconhecimento.titulo
            )
        )
        texto.append('<dl>')
        texto.append('<dt>Resumo da Base de Conhecimento:</dt><dd>{}</dd>'.format(baseconhecimento.resumo))
        texto.append('<dt>Comentário por {}:</dt><dd>{}</dd>'.format(usuario.get_profile().nome_usual, comentario))
        texto.append('</dl>')
        texto.append('<p>--</p>')
        texto.append('<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(baseconhecimento.get_visualizar_base_conhecimento_url()))
        if baseconhecimento.atualizado_por:
            send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [baseconhecimento.atualizado_por.get_vinculo()], objeto=baseconhecimento)

    @staticmethod
    def atendente_sobre_sla_estourado(chamado):
        from centralservicos.models import StatusChamado

        status = StatusChamado.STATUS[chamado.status]
        titulo = '[SUAP] Central de Serviços: Chamado com SLA estourado'
        texto = []
        texto.append('<h1>Chamado com SLA estourado</h1>')
        texto.append('<h2>#{} {}</h2>'.format(chamado.pk, chamado.servico.nome))
        texto.append('<p>Identificamos que este chamado atribuído à você está com o SLA estourado. Por favor, verifique-o.</p>')
        texto.append('<h3>Dados Gerais</h3>')
        texto.append('<dl>')
        template = Template('<dt>Descrição do Chamado:</dt><dd>{{descricao}}</dd>').render(Context({'descricao': chamado.descricao}))
        texto.append(template)
        texto.append('<dt>Interessado Principal:</dt><dd>{}</dd>'.format(chamado.interessado.get_profile().nome_usual))
        texto.append('<dt>Aberto em:</dt><dd>{}</dd>'.format(chamado.aberto_em.strftime("%d/%m/%Y %H:%M")))
        texto.append('<dt>Data de Estouro do SLA:</dt><dd>{}</dd>'.format(chamado.data_limite_atendimento.strftime("%d/%m/%Y %H:%M")))
        texto.append('<dt>Situação Atual:</dt><dd><strong>{}</strong>.</dd>'.format(status))
        texto.append('</dl>')
        texto.append('<p>--</p>')
        texto.append('<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(chamado.get_visualizar_chamado_url()))
        send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [chamado.get_atendimento_atribuicao_atual().atribuido_para.get_vinculo()], fail_silently=False, objeto=chamado)

    @staticmethod
    def responsavel_equipe_atendimento_sobre_sla_estourado(chamado):
        from centralservicos.models import StatusChamado

        status = StatusChamado.STATUS[chamado.status]
        titulo = '[SUAP] Central de Serviços: Chamado com SLA estourado'
        texto = []
        texto.append('<h1>Chamado com SLA estourado</h1>')
        texto.append('<h2>#{} {}</h2>'.format(chamado.pk, chamado.servico.nome))
        texto.append('<p>Você está recebendo este email porque está cadastrado como responsável pelo grupo de atendimento na central de serviços.</p>')
        atendimento_atribuicao = chamado.get_atendimento_atribuicao_atual()
        if atendimento_atribuicao and atendimento_atribuicao.atribuido_para:
            texto.append(
                '<p>Identificamos que este chamado, atribuído para <strong>{}</strong>, no Grupo de Atendimento {}, está com o SLA estourado.</p>'.format(
                    atendimento_atribuicao.atribuido_para, atendimento_atribuicao.grupo_atendimento.nome
                )
            )
        else:
            texto.append(
                '<p>Identificamos que este chamado <strong>(sem atribuição)</strong>, no Grupo de Atendimento {}, está com o SLA estourado.</p>'.format(
                    atendimento_atribuicao.grupo_atendimento.nome
                )
            )
        texto.append('<h3>Dados Gerais</h3>')
        texto.append('<dl>')
        template = Template('<dt>Descrição do Chamado:</dt><dd>{{descricao}}</dd>').render(Context({'descricao': chamado.descricao}))
        texto.append(template)
        texto.append('<dt>Interessado Principal:</dt><dd>{}</dd>'.format(chamado.interessado.get_profile().nome_usual))
        texto.append('<dt>Aberto em:</dt><dd>{}</dd>'.format(chamado.aberto_em.strftime("%d/%m/%Y %H:%M")))
        texto.append('<dt>Data de Estouro do SLA:</dt><dd>{}</dd>'.format(chamado.data_limite_atendimento.strftime("%d/%m/%Y %H:%M")))
        texto.append('<dt>Situação Atual:</dt><dd>{}.</dd>'.format(status))
        texto.append('</dl>')
        texto.append('<p>--</p>')
        texto.append('<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(chamado.get_visualizar_chamado_url()))
        if chamado.get_atendimento_atribuicao_atual().grupo_atendimento.email_responsaveis():
            send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, chamado.get_atendimento_atribuicao_atual().grupo_atendimento.get_vinculos_responsaveis(), fail_silently=False, objeto=chamado)
