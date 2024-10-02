import importlib
from datetime import datetime, date, timedelta, time

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.conf import settings
from comum.models import Predio, Sala, SolicitacaoReservaSala, ReservaSala, IndisponibilizacaoSala
from comum.tests.tests_base import SuapTestCase
from comum.utils import adicionar_mes, get_uo
from djtools.utils import prevent_logging_errors

# Perfil
GRUPO_SERVIDOR = 'Servidor'
GRUPO_AVALIADOR_SALA = 'Avaliador de Sala'


class AgendamentoSalaBaseTestCase(SuapTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(user=self.servidor_a.user)

        # Campus campus_a_suap tem salas agendáveis campus_b_suap não
        # criando prédios
        self.predio_agendavel = Predio.objects.get_or_create(nome='Anexo da Reitoria (RE)', uo=self.campus_a_suap, ativo=True)[0]
        self.predio_nao_agendavel = Predio.objects.get_or_create(nome='Prédio da Reitoria (RE)', uo=self.campus_b_suap, ativo=True)[0]

        # Populando 2 salas agendaveis, ativas e com avaliadores.
        self.sala_agendavel_a = Sala.objects.get_or_create(nome='Sala agendável AAA', ativa=True, predio=self.predio_agendavel, agendavel=True, capacidade=20)[0]
        self.sala_agendavel_a.avaliadores_de_agendamentos.add(self.servidor_a.user)

        self.sala_agendavel_b = Sala.objects.get_or_create(nome='Sala agendável BBB', ativa=True, predio=self.predio_agendavel, agendavel=True, capacidade=20)[0]
        self.sala_agendavel_b.avaliadores_de_agendamentos.add(self.servidor_b.user)

        # Sala inativa é agendável, possui avaliadores, mas não está ativa
        self.sala_inativa = Sala.objects.get_or_create(nome='Sala inativa', ativa=False, predio=self.predio_agendavel, agendavel=True, capacidade=20)[0]
        self.sala_inativa.avaliadores_de_agendamentos.add(self.servidor_a.user)

        # Sala sem avaliadores é agendável, está ativa mas não possui avaliadores
        self.sala_sem_avaliadores = Sala.objects.get_or_create(nome='Sala sem avaliadores', ativa=True, predio=self.predio_agendavel, agendavel=True, capacidade=20)[0]

        # Sala não agendável com avaliadores e ativa
        self.sala_nao_agendavel_a = Sala.objects.get_or_create(
            nome='Sala não agendável com avaliadores e ativa', ativa=True, predio=self.predio_agendavel, agendavel=False, capacidade=20
        )[0]
        self.sala_nao_agendavel_a.avaliadores_de_agendamentos.add(self.servidor_b.user)

        # Sala não agendável com avaliadores e inativa
        self.sala_nao_agendavel_b = Sala.objects.get_or_create(
            nome='Sala não agendável com avaliadores e inativa', ativa=False, predio=self.predio_agendavel, agendavel=False, capacidade=20
        )[0]
        self.sala_nao_agendavel_b.avaliadores_de_agendamentos.add(self.servidor_b.user)

        # Sala não agendável sem avaliadores e ativa
        self.sala_nao_agendavel_c = Sala.objects.get_or_create(
            nome='Sala não agendável sem avaliadores e ativa', ativa=True, predio=self.predio_agendavel, agendavel=False, capacidade=20
        )[0]

        # Sala não agendável sem avaliadores e inativa
        self.sala_nao_agendavel_d = Sala.objects.get_or_create(
            nome='Sala não agendável sem avaliadores e inativa', ativa=False, predio=self.predio_agendavel, agendavel=False, capacidade=20
        )[0]

        self.solicitacao_a = self.criar_solicitacao()
        self.solicitacao_b = self.criar_solicitacao(solicitante=self.servidor_b.user)

        self.solicitacao_atendida_a = self.criar_solicitacao(status=SolicitacaoReservaSala.STATUS_DEFERIDA)
        self.solicitacao_atendida_b = self.criar_solicitacao(solicitante=self.servidor_b.user, status=SolicitacaoReservaSala.STATUS_DEFERIDA)

        # criando solicitações para outra sala
        self.solicitacao_sala_b = self.criar_solicitacao(sala=self.sala_agendavel_b)
        self.solicitacao_sala_b_outro_usuario = self.criar_solicitacao(sala=self.sala_agendavel_b, solicitante=self.servidor_b.user)

        # Como vai trabalhar com o grupo 'Servidor' estou removendo ele para verificação
        self.servidor_a.user.groups.remove(Group.objects.get(name=GRUPO_SERVIDOR))
        self.servidor_b.user.groups.remove(Group.objects.get(name=GRUPO_SERVIDOR))
        self.servidor_c.user.groups.remove(Group.objects.get(name=GRUPO_SERVIDOR))
        self.servidor_d.user.groups.remove(Group.objects.get(name=GRUPO_SERVIDOR))

    def criar_solicitacao(self, sala=None, solicitante=None, **params):
        """
        Cria uma solicitação com os valores padrões se não for passado parâmetro
        """
        if not sala:
            sala = self.sala_agendavel_a

        if not solicitante:
            solicitante = self.servidor_a.user

        data_inicio = datetime.now() + timedelta(10)
        data_fim = datetime.now() + timedelta(10)
        init = dict(
            solicitante=solicitante,
            data_solicitacao=datetime.now(),
            sala=sala,
            recorrencia=SolicitacaoReservaSala.RECORRENCIA_EVENTO_UNICO,
            data_inicio=data_inicio.date(),
            data_fim=data_fim.date(),
            hora_inicio=time(8),
            hora_fim=time(10),
            justificativa='Contrato para prestacao algum serviço',
            recorrencia_segunda=False,
            recorrencia_terca=False,
            recorrencia_quarta=False,
            recorrencia_quinta=False,
            recorrencia_sexta=False,
            recorrencia_sabado=False,
            recorrencia_domingo=False,
        )
        init.update(params)
        if init.get("status"):
            init['data_avaliacao'] = datetime.now()

        solicitacao = SolicitacaoReservaSala.objects.create(**init)
        solicitacao = SolicitacaoReservaSala.objects.get(pk=solicitacao.pk)
        if solicitacao.status == SolicitacaoReservaSala.STATUS_DEFERIDA:
            solicitacao.gerar_reservas()

        return solicitacao

    def verificar_perfil_submit(
        self,
        url,
        data={},
        queryset=None,
        verificar_sem_perfil=True,
        pode_sem_perfil=False,
        perfis_corretos=(),
        perfis_errados=(),
        incremento=1,
        success_status_code=200,
        error_status_code=403,
        after_submit=None,
        modificou=None,
        contains_text=None,
        not_contains_text=None,
        user=None,
    ):
        """
        Verifica se está de acordo com os perfis
        Keyword arguments:
        after_submit -- Uma função a ser executada após cada submit
        """
        if not user:
            user = self.servidor_a.user

        qtd = queryset.count()
        if verificar_sem_perfil:
            for perfil in perfis_corretos:
                user.groups.remove(Group.objects.get(name=perfil))
            for perfil in perfis_errados:
                user.groups.remove(Group.objects.get(name=perfil))

            self.client.post(url, data)
            if pode_sem_perfil:
                qtd = queryset.count() + incremento
            if modificou:
                if pode_sem_perfil:
                    self.assertTrue(modificou())
                else:
                    self.assertFalse(modificou())
            self.assertEqual(queryset.count(), qtd, 'sem perfil {}!={}'.format(queryset.count(), qtd))
            if after_submit:
                after_submit()

        for perfil in perfis_corretos:
            qtd = queryset.count() + incremento
            user.groups.add(Group.objects.get(name=perfil))
            response = self.client.post(url, data)
            if not contains_text:
                self.assert_no_validation_errors(response, url, data, response.content)
            self.assertEqual(response.status_code, success_status_code, 'perfil correto {} {}!={}'.format(perfil, response.status_code, success_status_code))
            self.assertEqual(queryset.count(), qtd, 'perfil correto {} {}!={}'.format(perfil, queryset.count(), qtd))
            if contains_text or not_contains_text:
                if response.get('Location'):
                    # Utilizado para recuperar a mensagem
                    response = self.client.get(response.get('Location'), {})
                if contains_text:
                    self.assertContains(response, text=contains_text, msg_prefix='perfil correto {}'.format(perfil))
                if not_contains_text:
                    self.assertNotContains(response, text=not_contains_text, msg_prefix='perfil correto {}'.format(perfil))
            if modificou:
                self.assertTrue(modificou(), "perfil {} não modificou".format(perfil))
            if after_submit:
                after_submit()
            user.groups.remove(Group.objects.get(name=perfil))

        # TODO: Verificar se é melhor mudar o comportamento do admin para lança um 403 aos inves de um 404 no caso de um objeto que não está no queryset
        if url.startswith('/admin/'):
            error_status_code = [error_status_code, 404]

        for perfil in perfis_errados:
            qtd = queryset.count()
            user.groups.add(Group.objects.get(name=perfil))
            response = self.client.post(url, data, silent=True)
            content = self.client.post(url, data, silent=True, follow=True).content
            if isinstance(error_status_code, list):
                self.assertIn(response.status_code, error_status_code, "perfil errado {} {}!={} {}-{} {}".format(perfil, response.status_code, error_status_code, url, data, content))
            else:
                self.assertEqual(response.status_code, error_status_code, "perfil errado {} {}!={} {}-{} {}".format(perfil, response.status_code, error_status_code, url, data, content))
            self.assertEqual(queryset.count(), qtd, 'perfil errado {} {}!={}'.format(perfil, queryset.count(), qtd))
            if modificou:
                self.assertFalse(modificou(), "perfil {} modificou".format(perfil))
            if after_submit:
                after_submit()
            user.groups.remove(Group.objects.get(name=perfil))

    def verificar_perfil_alterar(
        self,
        url,
        data={},
        verificar_sem_perfil=True,
        pode_sem_perfil=False,
        perfis_corretos=[],
        perfis_errados=[],
        modificou=None,
        success_status_code=200,
        error_status_code=403,
        after_submit=None,
        user=None,
    ):
        """
        Verifica se está de acordo com os perfis
        Keyword arguments:
        after_submit -- Uma função a ser executada após cada submit
        """
        if not user:
            user = self.servidor_a.user

        if verificar_sem_perfil:
            for perfil in perfis_corretos:
                user.groups.remove(Group.objects.get(name=perfil))
            for perfil in perfis_errados:
                user.groups.remove(Group.objects.get(name=perfil))

            self.client.post(url, data)
            if pode_sem_perfil:
                self.assertTrue(modificou())
            else:
                self.assertFalse(modificou())
            if after_submit:
                after_submit()

        for perfil in perfis_corretos:
            user.groups.add(Group.objects.get(name=perfil))
            response = self.client.post(url, data)
            self.assertEqual(response.status_code, success_status_code, 'perfil correto {} {}!={}'.format(perfil, response.status_code, success_status_code))
            if modificou:
                self.assertTrue(modificou(), "perfil {} não modificou".format(perfil))
            if after_submit:
                after_submit()
            user.groups.remove(Group.objects.get(name=perfil))

        # TODO: Verificar se é melhor mudar o comportamento do admin para lança um 403 aos inves de um 404 no caso de um objeto que não está no queryset
        if url.startswith('/admin/'):
            error_status_code = [error_status_code, 404]

        for perfil in perfis_errados:
            user.groups.add(Group.objects.get(name=perfil))
            response = self.client.post(url, data, silent=True)
            if isinstance(error_status_code, list):
                self.assertIn(response.status_code, error_status_code, "perfil errado {} {}!={}".format(perfil, response.status_code, error_status_code))
            else:
                self.assertEqual(response.status_code, error_status_code, "perfil errado {} {}!={}".format(perfil, response.status_code, error_status_code))
            if modificou:
                self.assertFalse(modificou(), "perfil {} modificou".format(perfil))
            if after_submit:
                after_submit()
            user.groups.remove(Group.objects.get(name=perfil))

    def verificar_perfil_remover(
        self,
        url_base,
        url_params=[],
        data={},
        queryset=None,
        verificar_sem_perfil=True,
        pode_sem_perfil=False,
        perfis_corretos=[],
        perfis_errados=[],
        incremento=-1,
        success_status_code=200,
        user=None,
    ):
        """
        Verifica se está de acordo com os perfis
        Keyword arguments:
        after_submit -- Uma função a ser executada após cada submit
        """
        if not user:
            user = self.servidor_a.user

        url_params.reverse()

        def get_url(url, params):
            return url.format(params.pop()) if params else url

        # Verifica se é admin, por ele tem um input hidden no caso de remoção
        if url_base.startswith('/admin/'):
            data.update(dict(post='yes'))
            success_status_code = 302

        qtd = queryset.count()
        if verificar_sem_perfil:
            for perfil in perfis_corretos:
                user.groups.remove(Group.objects.get(name=perfil))
            for perfil in perfis_errados:
                user.groups.remove(Group.objects.get(name=perfil))

            url = get_url(url_base, url_params)
            response = self.client.post(url, data)
            if pode_sem_perfil:
                qtd += incremento
                self.assertEqual(response.status_code, success_status_code, 'sem perfil {}!={}'.format(response.status_code, success_status_code))
            else:
                self.assertNotEqual(response.status_code, success_status_code, 'sem perfil {}=={}'.format(response.status_code, success_status_code))

            self.assertEqual(queryset.count(), qtd, 'sem perfil {}!={}'.format(queryset.count(), qtd))

        for perfil in perfis_corretos:
            qtd += incremento
            user.groups.add(Group.objects.get(name=perfil))
            url = get_url(url_base, url_params)
            response = self.client.post(url, data)
            self.assertEqual(response.status_code, success_status_code, 'perfil correto {} {}!={}'.format(perfil, response.status_code, success_status_code))
            self.assertEqual(queryset.count(), qtd, 'perfil correto {} {}!={}'.format(perfil, queryset.count(), qtd))
            user.groups.remove(Group.objects.get(name=perfil))

        for perfil in perfis_errados:
            user.groups.add(Group.objects.get(name=perfil))
            url = get_url(url_base, url_params)
            response = self.client.post(url, data)
            self.assertNotEqual(response.status_code, success_status_code, 'perfil errado {} {}=={}'.format(perfil, response.status_code, success_status_code))
            self.assertEqual(queryset.count(), qtd, 'perfil errado {} {}!={}'.format(perfil, queryset.count(), qtd))
            user.groups.remove(Group.objects.get(name=perfil))

    def verificar_envio_email(self, to, subject, qtd=1):
        from django.core import mail

        if type(to) is list:
            emails = []
            for _ in to:
                email = mail.outbox.pop()
                emails.extend(email.to)
        else:
            email = mail.outbox.pop()
            emails = email.to
            to = [to]

        # Test the number of messages sent.
        self.assertEqual(len(to), len(emails))
        # Verify that the subject of the first message is correct.
        self.assertEqual(email.subject, subject)
        self.assertEqual(set(emails), set(to))
        mail.outbox = list()


class SolicitacaoReservaSalaTestCase(AgendamentoSalaBaseTestCase):
    def get_dados(self):
        data = (datetime.now() + timedelta(10)).replace(hour=8, minute=0, second=0, microsecond=0)
        return dict(
            recorrencia=SolicitacaoReservaSala.RECORRENCIA_EVENTO_UNICO,
            data_inicio=data.strftime('%Y-%m-%d'),
            hora_inicio=datetime.strptime('08:00', '%H:%M').time(),
            data_fim=data.replace(hour=12).strftime('%Y-%m-%d'),
            hora_fim=datetime.strptime('12:00', '%H:%M').time(),
            justificativa='Contrato para prestacao algum serviço',
            interessados_vinculos=[self.servidor_c.get_vinculo().id],
        )

    @prevent_logging_errors()
    def test_listar(self):
        """
        1. Só o perfil de Servidor pode listar
        2. Só pode ver solicitações criadas por ele
        """
        # Verificação do defaul que é a aba "qualquer"
        url = '/admin/comum/solicitacaoreservasala/'
        self.verificar_perfil_status(url, perfis_corretos=[GRUPO_SERVIDOR])
        # solicitações do usuário
        self.verificar_perfil_contains(url, text='href="/comum/sala/ver_solicitacao/{:d}/"'.format(self.solicitacao_a.id), perfis_corretos=[GRUPO_SERVIDOR])
        self.verificar_perfil_contains(url, text='href="/comum/sala/ver_solicitacao/{:d}/"'.format(self.solicitacao_atendida_a.id), perfis_corretos=[GRUPO_SERVIDOR])
        # solicitações de outro usuário
        self.verificar_perfil_not_contains(url, text='href="/comum/sala/ver_solicitacao/{:d}/"'.format(self.solicitacao_b.id), perfis_corretos=[GRUPO_SERVIDOR])
        self.verificar_perfil_not_contains(url, text='href="/comum/sala/ver_solicitacao/{:d}/"'.format(self.solicitacao_atendida_b.id), perfis_corretos=[GRUPO_SERVIDOR])

        # Verificação por "pendentes"
        url = '/admin/comum/solicitacaoreservasala/?status__exact=aguardando_avaliacao'
        self.verificar_perfil_status(url, perfis_corretos=[GRUPO_SERVIDOR])
        # solicitações do usuário
        self.verificar_perfil_contains(url, text='href="/comum/sala/ver_solicitacao/{:d}/"'.format(self.solicitacao_a.id), perfis_corretos=[GRUPO_SERVIDOR])
        self.verificar_perfil_not_contains(url, text='href="/comum/sala/ver_solicitacao/{:d}/"'.format(self.solicitacao_atendida_a.id), perfis_corretos=[GRUPO_SERVIDOR])
        # solicitações de outro usuário
        self.verificar_perfil_not_contains(url, text='href="/comum/sala/ver_solicitacao/{:d}/"'.format(self.solicitacao_b.id), perfis_corretos=[GRUPO_SERVIDOR])
        self.verificar_perfil_not_contains(url, text='href="/comum/sala/ver_solicitacao/{:d}/"'.format(self.solicitacao_atendida_b.id), perfis_corretos=[GRUPO_SERVIDOR])

        # Verificação por "atendidas"
        url = '/admin/comum/solicitacaoreservasala/?status__exact=deferida'
        self.verificar_perfil_status(url, perfis_corretos=[GRUPO_SERVIDOR])
        # solicitações do usuário
        self.verificar_perfil_contains(url, text='href="/comum/sala/ver_solicitacao/{:d}/"'.format(self.solicitacao_atendida_a.id), perfis_corretos=[GRUPO_SERVIDOR])
        self.verificar_perfil_not_contains(url, text='href="/comum/sala/ver_solicitacao/{:d}/"'.format(self.solicitacao_a.id), perfis_corretos=[GRUPO_SERVIDOR])
        # solicitações de outro usuário
        self.verificar_perfil_not_contains(url, text='href="/comum/sala/ver_solicitacao/{:d}/"'.format(self.solicitacao_atendida_b.id), perfis_corretos=[GRUPO_SERVIDOR])
        self.verificar_perfil_not_contains(url, text='href="/comum/sala/ver_solicitacao/{:d}/"'.format(self.solicitacao_b.id), perfis_corretos=[GRUPO_SERVIDOR])

        # Teste da busca
        # dados do filtro
        dados_filtro = {'q': self.sala_agendavel_b.nome}
        url = '/admin/comum/solicitacaoreservasala/'
        self.verificar_perfil_status(url, perfis_corretos=[GRUPO_SERVIDOR])
        # solicitações do usuário, só pode ver a da sala do filtro
        self.verificar_perfil_contains(url, dados_filtro, text='href="/comum/sala/ver_solicitacao/{:d}/"'.format(self.solicitacao_sala_b.id), perfis_corretos=[GRUPO_SERVIDOR])
        self.verificar_perfil_not_contains(url, dados_filtro, text='href="/comum/sala/ver_solicitacao/{:d}/"'.format(self.solicitacao_a.id), perfis_corretos=[GRUPO_SERVIDOR])
        self.verificar_perfil_not_contains(
            url, dados_filtro, text='href="/comum/sala/ver_solicitacao/{:d}/"'.format(self.solicitacao_atendida_a.id), perfis_corretos=[GRUPO_SERVIDOR]
        )
        # solicitações de outro usuário
        self.verificar_perfil_not_contains(
            url, dados_filtro, text='href="/comum/sala/ver_solicitacao/{:d}/"'.format(self.solicitacao_sala_b_outro_usuario.id), perfis_corretos=[GRUPO_SERVIDOR]
        )
        self.verificar_perfil_not_contains(url, dados_filtro, text='href="/comum/sala/ver_solicitacao/{:d}/"'.format(self.solicitacao_b.id), perfis_corretos=[GRUPO_SERVIDOR])
        self.verificar_perfil_not_contains(
            url, dados_filtro, text='href="/comum/sala/ver_solicitacao/{:d}/"'.format(self.solicitacao_atendida_b.id), perfis_corretos=[GRUPO_SERVIDOR]
        )

    @prevent_logging_errors()
    def test_cadastrar_enviar_email(self):
        """
        1. Só o perfil de Servidor pode cadastrar
        2. UC 02 - Primeira pós-condição (É enviado um e-mail para os avaliadores informando sobre a reserva;)
        3. UC 02 - RN11 (Os servidores informados em Compartilhar com receberão email sobre a solicitação de reservas, bem como sobre o resultado da avaliação da reserva.)
        """
        SolicitacaoReservaSala.objects.all().delete()
        dados = self.get_dados()
        # avaliador é o servidor_b
        url = '/comum/sala/solicitar_reserva/{:d}/'.format(self.sala_agendavel_b.id)
        url_base = '/admin/comum/sala/?agendavel__exact=1&predio__uo={:d}'.format(get_uo(self.servidor_a.get_user()).id)

        # Todo servidor pode
        self.servidor_a.user.groups.add(Group.objects.get(name=GRUPO_SERVIDOR))
        self.client.get('/admin/comum/solicitacaoreservasala/add/')

        self.servidor_a.user.groups.remove(Group.objects.get(name=GRUPO_SERVIDOR))

        self.verificar_perfil_contains(url_base, text='href="{}"'.format(url), perfis_corretos=[GRUPO_SERVIDOR])
        self.verificar_perfil_submit(url, dados, SolicitacaoReservaSala.objects, perfis_corretos=[GRUPO_SERVIDOR], success_status_code=302)

        # Verificando o envio de email para o requisitante,
        requisitante_email = self.servidor_a.email
        interessado_email = self.servidor_c.email
        avaliador_email = self.servidor_b.email  # Avaliador da sala B
        self.verificar_envio_email([requisitante_email, interessado_email, avaliador_email], '[SUAP] Reservas de Salas: Nova Solicitação')

    @prevent_logging_errors()
    def test_cadastrar_e_ver_painel_notificacao(self):
        """
        1. Só o perfil de Servidor pode cadastrar
        2. Só o perfil de Servidor e que é avaliador de sala pode ver o painel
        3. UC 02 - Segunda pós-condição (É incluso no Painel de Notificação do avaliador um aviso de que existem agendamentos pendentes de avaliação.)
        """
        SolicitacaoReservaSala.objects.all().delete()
        # o Avaliador é o servidor_a
        self.solicitacao_b.save()
        texto_sala = 'Solicitação de Sala'

        self.verificar_perfil_contains('/', text=texto_sala, perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR])
        # o servidor_b não é avaliador da sala da solicitacao_b
        self.client.logout()
        self.client.login(user=self.servidor_b.user)
        self.verificar_perfil_not_contains('/', text=texto_sala, perfis_corretos=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR])
        # o servidor_c não é avaliador de nenhuma sala
        self.client.logout()
        self.client.login(user=self.servidor_c.user)
        self.verificar_perfil_not_contains('/', text=texto_sala, perfis_corretos=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR])

    @prevent_logging_errors()
    def test_cadastrar_conflito_reserva(self):
        """
        1. Só o perfil de Servidor pode cadastrar
        2. UC 02 - RN2 (Não deve existir duas solicitações de salas avaliadas na mesma data/hora.)
        """
        SolicitacaoReservaSala.objects.all().delete()
        solicitacao_atendida = self.criar_solicitacao(status=SolicitacaoReservaSala.STATUS_DEFERIDA)
        # criado para submeter com os mesmo dados da solicitacao_atendida_a para dar o conflito
        dados = self.get_dados()
        dados_agendada = dados.copy()
        dados_agendada['data_inicio'] = solicitacao_atendida.data_inicio.strftime('%Y-%m-%d')
        dados_agendada['hora_inicio'] = solicitacao_atendida.hora_inicio.strftime('%H:%M:%S')
        dados_agendada['data_fim'] = solicitacao_atendida.data_fim.strftime('%Y-%m-%d')
        dados_agendada['hora_fim'] = solicitacao_atendida.hora_fim.strftime('%H:%M:%S')
        url = '/comum/sala/solicitar_reserva/{:d}/'.format(solicitacao_atendida.sala.id)
        # não irá cadastrar e
        self.verificar_perfil_submit(url, dados_agendada, SolicitacaoReservaSala.objects, incremento=0, contains_text='Sala já está reservada para a data e hora especificadas.')
        # Após apagar ela não existirá nehum impedimento
        solicitacao_atendida.delete()
        self.verificar_perfil_submit(
            url,
            dados_agendada,
            SolicitacaoReservaSala.objects,
            perfis_corretos=[GRUPO_SERVIDOR],
            success_status_code=302,
            not_contains_text='Sala já está reservada para a data e hora especificadas.',
        )

    @prevent_logging_errors()
    def test_apagar(self):
        """
        1. Só o perfil de Servidor pode excluir
        2. Só o solicitante pode excluir a solicitação
        3. RN9 (Critério para exibição da opção excluir: essa opção só estará disponível se a solicitação de reserva ainda não foi avaliada.)
        """
        url_base = '/admin/comum/solicitacaoreservasala/'
        url = '/comum/sala/excluir_solicitacao/{:d}/'.format(self.solicitacao_a.id)
        self.verificar_perfil_contains(url_base, text='href="{}"'.format(url), perfis_corretos=[GRUPO_SERVIDOR])
        url = '/comum/sala/excluir_solicitacao/{:d}/'.format(self.solicitacao_atendida_a.id)
        self.verificar_perfil_not_contains(url_base, text='href="{}"'.format(url), perfis_corretos=[GRUPO_SERVIDOR])

        # Já está testando em test_listar alguma pendente
        url_base = '/admin/comum/solicitacaoreservasala/?status__exact=aguardando_avaliacao'
        url = '/comum/sala/excluir_solicitacao/{:d}/'.format(self.solicitacao_a.id)
        self.verificar_perfil_contains(url_base, text='href="{}"'.format(url), perfis_corretos=[GRUPO_SERVIDOR])

        # Já está testando em test_listar se aparece alguma atendida
        url_base = '/admin/comum/solicitacaoreservasala/?status__exact=deferida'
        url = '/comum/sala/excluir_solicitacao/{:d}/'.format(self.solicitacao_atendida_a.id)
        self.verificar_perfil_not_contains(url_base, text='href="{}"'.format(url), perfis_corretos=[GRUPO_SERVIDOR])

        # criando os objetos para testar a exclusão
        # do usuário logado
        solicitacao_pendente = self.criar_solicitacao()
        solicitacao_atendida = self.criar_solicitacao(status=SolicitacaoReservaSala.STATUS_DEFERIDA)
        # de outro usuário
        solicitacao_pendente_outro = self.criar_solicitacao(solicitante=self.servidor_b.user)
        solicitacao_atendida_outro = self.criar_solicitacao(solicitante=self.servidor_b.user)

        url_base = '/comum/sala/excluir_solicitacao/{:d}/'
        # Só pode excluir a Solicitação Pendente do usuario
        qtd = SolicitacaoReservaSala.objects.count()
        self.verificar_perfil_remover(
            url_base, [solicitacao_pendente.id, solicitacao_pendente.id], queryset=SolicitacaoReservaSala.objects.exclude(status=SolicitacaoReservaSala.STATUS_EXCLUIDA), perfis_corretos=[GRUPO_SERVIDOR], success_status_code=302
        )
        self.assertEqual(SolicitacaoReservaSala.objects.count(), qtd)
        # Não exclui pois já está atendida
        qtd = SolicitacaoReservaSala.objects.count()
        self.verificar_perfil_remover(
            url_base, [solicitacao_atendida.id, solicitacao_atendida.id], queryset=SolicitacaoReservaSala.objects.all(), perfis_errados=[GRUPO_SERVIDOR], success_status_code=302
        )
        self.assertEqual(SolicitacaoReservaSala.objects.count(), qtd)
        # Não exclui pois é de outro usuário
        qtd = SolicitacaoReservaSala.objects.count()
        self.verificar_perfil_remover(
            url_base,
            [solicitacao_pendente_outro.id, solicitacao_pendente_outro.id],
            queryset=SolicitacaoReservaSala.objects.all(),
            perfis_errados=[GRUPO_SERVIDOR],
            success_status_code=302,
        )
        self.assertEqual(SolicitacaoReservaSala.objects.count(), qtd)
        # Não exclui pois é de outro usuário e já está atendida
        qtd = SolicitacaoReservaSala.objects.count()
        self.verificar_perfil_remover(
            url_base,
            [solicitacao_atendida_outro.id, solicitacao_atendida_outro.id],
            queryset=SolicitacaoReservaSala.objects.all(),
            perfis_errados=[GRUPO_SERVIDOR],
            success_status_code=302,
        )
        self.assertEqual(SolicitacaoReservaSala.objects.count(), qtd)

    @prevent_logging_errors()
    def test_visualizar(self):
        """
        1. Só o perfil de Servidor pode visualizar
        2. Só o solicitante ou um avaliador da sala pode visualizar a solicitação
        """
        # Solicitações dele, ele pode ver
        url = '/comum/sala/ver_solicitacao/{:d}/'.format(self.solicitacao_a.id)
        self.verificar_perfil_status(url, perfis_corretos=[GRUPO_SERVIDOR])
        self.verificar_perfil_contains(url, text='Solicitação de Reserva de Sala', perfis_corretos=[GRUPO_SERVIDOR])
        url = '/comum/sala/ver_solicitacao/{:d}/'.format(self.solicitacao_atendida_a.id)
        self.verificar_perfil_status(url, perfis_corretos=[GRUPO_SERVIDOR])
        self.verificar_perfil_contains(url, text='Solicitação de Reserva de Sala', perfis_corretos=[GRUPO_SERVIDOR])
        url = '/comum/sala/ver_solicitacao/{:d}/'.format(self.solicitacao_sala_b.id)
        self.verificar_perfil_status(url, perfis_corretos=[GRUPO_SERVIDOR])
        self.verificar_perfil_contains(url, text='Solicitação de Reserva de Sala', perfis_corretos=[GRUPO_SERVIDOR])

        # Solicitações de outro mas ele pode ver como é avaliador da sala_agendavel_a
        url = '/comum/sala/ver_solicitacao/{:d}/'.format(self.solicitacao_b.id)
        self.verificar_perfil_status(url, perfis_corretos=[GRUPO_AVALIADOR_SALA])
        url = '/comum/sala/ver_solicitacao/{:d}/'.format(self.solicitacao_atendida_b.id)
        self.verificar_perfil_status(url, perfis_corretos=[GRUPO_AVALIADOR_SALA])

        # ele não pode ver pois não é avaliador da sala_agendavel_b
        url = '/comum/sala/ver_solicitacao/{:d}/'.format(self.solicitacao_sala_b_outro_usuario.id)
        self.verificar_perfil_status(url)

    @prevent_logging_errors()
    def test_cancelar_solicitacao(self):
        """
        1. Só o solicitante pode cancelar uma solicitação
        2. É enviado um e-mail para os avaliadores e interessados de reserva informando que a reserva foi cancelada;
        """

        def desmodificar(solicitacao):
            solicitacao.data_avaliacao = None
            solicitacao.avaliador = None
            solicitacao.observacao_avaliador = ""
            solicitacao.status = SolicitacaoReservaSala.STATUS_AGUARDANDO_AVALIACAO
            solicitacao.save()
            solicitacao.reservasala_set.all().delete()

        def modificou(solicitacao):
            solicitacao = SolicitacaoReservaSala.objects.get(id=solicitacao.id)
            # o status fica como indeferida
            modificou = solicitacao.status == SolicitacaoReservaSala.STATUS_INDEFERIDA
            # se tiver reserva são todas canceladas
            modificou = modificou and not solicitacao.reservasala_set.exclude(cancelada=True).exists()
            return modificou

        # usuario_b fez a solicitação solicitacao_b
        url_base = '/comum/sala/ver_solicitacao/{:d}/'.format(self.solicitacao_b.id)
        url = '/comum/sala/cancelar_solicitacao/{:d}/'.format(self.solicitacao_b.id)
        dados = {'justificativa_cancelamento': 'teste'}
        self.solicitacao_b.interessados_vinculos.add(self.servidor_c.get_vinculo())
        self.client.logout()
        self.client.login(user=self.servidor_b.user)

        # Verifica se existe o link para cancelamento
        self.verificar_perfil_contains(
            url_base, text='href="{}"'.format(url), perfis_corretos=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR], error_status_code=403, user=self.servidor_b.user
        )
        # Avalia a solicitação
        self.verificar_perfil_status(url, pode_sem_perfil=True, user=self.servidor_b.user)
        self.verificar_perfil_submit(
            url,
            dados,
            SolicitacaoReservaSala.objects,
            pode_sem_perfil=True,
            incremento=0,
            after_submit=lambda: desmodificar(self.solicitacao_b),
            modificou=lambda: modificou(self.solicitacao_b),
            user=self.servidor_b.user,
        )

        # É enviado um e-mail para os avaliadores e interessados de reserva informando que a reserva foi cancelada;
        interessado_email = self.servidor_c.email
        avaliador_email = self.servidor_a.email
        self.verificar_envio_email([interessado_email, avaliador_email], '[SUAP] Reservas de Salas: Solicitação Cancelada')

        # usuario_a não é o solicitante da sala
        self.client.logout()
        self.client.login(user=self.servidor_a.user)
        # Verifica se não existe o link para avaliação
        self.verificar_perfil_not_contains(url_base, text='href="{}"'.format(url), pode_sem_perfil=True, success_status_code=403)
        self.verificar_perfil_status(url, perfis_errados=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR])
        self.verificar_perfil_submit(
            url,
            dados,
            SolicitacaoReservaSala.objects,
            perfis_errados=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR],
            after_submit=lambda: desmodificar(self.solicitacao_b),
            modificou=lambda: modificou(self.solicitacao_b),
        )

        # Cancelando reserva já deferida
        self.solicitacao_b.status = SolicitacaoReservaSala.STATUS_DEFERIDA
        self.solicitacao_b.save()
        self.solicitacao_b.gerar_reservas()
        self.client.logout()
        self.client.login(user=self.servidor_b.user)
        # Verifica se existe o link para cancelamento
        self.verificar_perfil_contains(
            url_base, text='href="{}"'.format(url), perfis_corretos=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR], error_status_code=403, user=self.servidor_b.user
        )
        # Avalia a solicitação
        self.verificar_perfil_status(url, pode_sem_perfil=True, user=self.servidor_b.user)
        self.verificar_perfil_submit(
            url,
            dados,
            SolicitacaoReservaSala.objects,
            pode_sem_perfil=True,
            incremento=0,
            after_submit=lambda: desmodificar(self.solicitacao_b),
            modificou=lambda: modificou(self.solicitacao_b),
            user=self.servidor_b.user,
        )

    @prevent_logging_errors()
    def test_get_datas_solicitadas(self):
        """
            Verifica se são retornados as datas com hora reais, levando em consideração a recorrência
        """
        # Data base da reserva de sala
        data_base = date(2500, 0o1, 0o1)
        # EVENTO UNICO
        solicitacao_unica_1 = self.criar_solicitacao(
            data_inicio=data_base + timedelta(1),
            data_fim=data_base + timedelta(1),
            hora_inicio=time(7),
            hora_fim=time(12),
            recorrencia=SolicitacaoReservaSala.RECORRENCIA_EVENTO_UNICO,
        )
        datas = [[datetime(2500, 1, 2, 7), datetime(2500, 1, 2, 12)]]
        self.assertEqual(solicitacao_unica_1.get_datas_solicitadas(), datas)

        solicitacao_unica_2 = self.criar_solicitacao(
            data_inicio=data_base,
            data_fim=data_base + timedelta(15),
            hora_inicio=time(10, 30),
            hora_fim=time(11, 30),
            recorrencia=SolicitacaoReservaSala.RECORRENCIA_EVENTO_UNICO,
            recorrencia_segunda=True,
            recorrencia_quarta=True,
            recorrencia_sexta=True,
        )
        datas = [[datetime(2500, 1, 1, 10, 30), datetime(2500, 1, 16, 11, 30)]]
        self.assertEqual(solicitacao_unica_2.get_datas_solicitadas(), datas)

        solicitacao_unica_3 = self.criar_solicitacao(
            data_inicio=data_base,
            data_fim=data_base + timedelta(7),
            hora_inicio=time(8),
            hora_fim=time(10),
            recorrencia=SolicitacaoReservaSala.RECORRENCIA_EVENTO_UNICO,
            recorrencia_terca=True,
            recorrencia_quinta=True,
            recorrencia_sabado=True,
            recorrencia_domingo=True,
        )
        datas = [[datetime(2500, 1, 1, 8), datetime(2500, 1, 8, 10)]]
        self.assertEqual(solicitacao_unica_3.get_datas_solicitadas(), datas)

        # SEMANALMENTE
        solicitacao_semanal_1 = self.criar_solicitacao(
            data_inicio=data_base,
            data_fim=data_base + timedelta(15),
            hora_inicio=time(10),
            hora_fim=time(12),
            recorrencia=SolicitacaoReservaSala.RECORRENCIA_SEMANALMENTE,
            recorrencia_segunda=True,
            recorrencia_quarta=True,
            recorrencia_sexta=True,
        )
        # sexta                                                segunda
        datas = [
            [datetime(2500, 1, 1, 10), datetime(2500, 1, 1, 12)],
            [datetime(2500, 1, 4, 10), datetime(2500, 1, 4, 12)],
            # quarta                                               sexta
            [datetime(2500, 1, 6, 10), datetime(2500, 1, 6, 12)],
            [datetime(2500, 1, 8, 10), datetime(2500, 1, 8, 12)],
            # segunda                                                quarta
            [datetime(2500, 1, 11, 10), datetime(2500, 1, 11, 12)],
            [datetime(2500, 1, 13, 10), datetime(2500, 1, 13, 12)],
            # sexta
            [datetime(2500, 1, 15, 10), datetime(2500, 1, 15, 12)],
        ]
        self.assertEqual(solicitacao_semanal_1.get_datas_solicitadas(), datas)

        solicitacao_semanal_2 = self.criar_solicitacao(
            data_inicio=data_base,
            data_fim=data_base + timedelta(7),
            hora_inicio=time(8),
            hora_fim=time(10),
            recorrencia=SolicitacaoReservaSala.RECORRENCIA_SEMANALMENTE,
            recorrencia_terca=True,
            recorrencia_quinta=True,
            recorrencia_sabado=True,
            recorrencia_domingo=True,
        )
        # sábado                                               domingo
        datas = [
            [datetime(2500, 1, 2, 8), datetime(2500, 1, 2, 10)],
            [datetime(2500, 1, 3, 8), datetime(2500, 1, 3, 10)],
            # terça                                                quinta
            [datetime(2500, 1, 5, 8), datetime(2500, 1, 5, 10)],
            [datetime(2500, 1, 7, 8), datetime(2500, 1, 7, 10)],
        ]
        self.assertEqual(solicitacao_semanal_2.get_datas_solicitadas(), datas)

        # QUINZENALMENTE
        solicitacao_quinzenal_1 = self.criar_solicitacao(
            data_inicio=data_base,
            data_fim=data_base + timedelta(45),
            hora_inicio=time(10),
            hora_fim=time(12),
            recorrencia=SolicitacaoReservaSala.RECORRENCIA_QUINZENALMENTE,
            recorrencia_segunda=True,
            recorrencia_quarta=True,
            recorrencia_sexta=True,
        )
        # sexta                                                segunda
        datas = [
            [datetime(2500, 1, 1, 10), datetime(2500, 1, 1, 12)],
            [datetime(2500, 1, 4, 10), datetime(2500, 1, 4, 12)],
            # quarta
            [datetime(2500, 1, 6, 10), datetime(2500, 1, 6, 12)],
            # sexta
            [datetime(2500, 1, 15, 10), datetime(2500, 1, 15, 12)],
            # segunda                                                quarta
            [datetime(2500, 1, 18, 10), datetime(2500, 1, 18, 12)],
            [datetime(2500, 1, 20, 10), datetime(2500, 1, 20, 12)],
            # sexta
            [datetime(2500, 1, 29, 10), datetime(2500, 1, 29, 12)],
            # segunda                                                quarta
            [datetime(2500, 2, 1, 10), datetime(2500, 2, 1, 12)],
            [datetime(2500, 2, 3, 10), datetime(2500, 2, 3, 12)],
            # sexta                                                  segunda
            [datetime(2500, 2, 12, 10), datetime(2500, 2, 12, 12)],
            [datetime(2500, 2, 15, 10), datetime(2500, 2, 15, 12)],
        ]
        self.assertEqual(solicitacao_quinzenal_1.get_datas_solicitadas(), datas)

        solicitacao_quinzenal_2 = self.criar_solicitacao(
            data_inicio=data_base,
            data_fim=data_base + timedelta(30),
            hora_inicio=time(8),
            hora_fim=time(10),
            recorrencia=SolicitacaoReservaSala.RECORRENCIA_QUINZENALMENTE,
            recorrencia_terca=True,
            recorrencia_quinta=True,
            recorrencia_sabado=True,
            recorrencia_domingo=True,
        )
        # sábado                                               domingo
        datas = [
            [datetime(2500, 1, 2, 8), datetime(2500, 1, 2, 10)],
            [datetime(2500, 1, 3, 8), datetime(2500, 1, 3, 10)],
            # terça                                                quinta
            [datetime(2500, 1, 5, 8), datetime(2500, 1, 5, 10)],
            [datetime(2500, 1, 7, 8), datetime(2500, 1, 7, 10)],
            # sábado                                               domingo
            [datetime(2500, 1, 16, 8), datetime(2500, 1, 16, 10)],
            [datetime(2500, 1, 17, 8), datetime(2500, 1, 17, 10)],
            # terça                                                quinta
            [datetime(2500, 1, 19, 8), datetime(2500, 1, 19, 10)],
            [datetime(2500, 1, 21, 8), datetime(2500, 1, 21, 10)],
            # sábado                                               domingo
            [datetime(2500, 1, 30, 8), datetime(2500, 1, 30, 10)],
            [datetime(2500, 1, 31, 8), datetime(2500, 1, 31, 10)],
        ]
        self.assertEqual(solicitacao_quinzenal_2.get_datas_solicitadas(), datas)

        # MENSALMENTE
        solicitacao_mensal_1 = self.criar_solicitacao(
            data_inicio=data_base,
            data_fim=adicionar_mes(data_base + timedelta(-1), 4),
            hora_inicio=time(10),
            hora_fim=time(12),
            recorrencia=SolicitacaoReservaSala.RECORRENCIA_MENSALMENTE,
            recorrencia_segunda=True,
            recorrencia_quarta=True,
            recorrencia_sexta=True,
        )
        # sexta                                                segunda
        datas = [
            [datetime(2500, 1, 1, 10), datetime(2500, 1, 1, 12)],
            [datetime(2500, 1, 4, 10), datetime(2500, 1, 4, 12)],
            # quarta
            [datetime(2500, 1, 6, 10), datetime(2500, 1, 6, 12)],
            # segunda
            [datetime(2500, 2, 1, 10), datetime(2500, 2, 1, 12)],
            # quarta                                                sexta
            [datetime(2500, 2, 3, 10), datetime(2500, 2, 3, 12)],
            [datetime(2500, 2, 5, 10), datetime(2500, 2, 5, 12)],
            # segunda
            [datetime(2500, 3, 1, 10), datetime(2500, 3, 1, 12)],
            # quarta                                                sexta
            [datetime(2500, 3, 3, 10), datetime(2500, 3, 3, 12)],
            [datetime(2500, 3, 5, 10), datetime(2500, 3, 5, 12)],
            # sexta
            [datetime(2500, 4, 2, 10), datetime(2500, 4, 2, 12)],
            # segunda                                                quarta
            [datetime(2500, 4, 5, 10), datetime(2500, 4, 5, 12)],
            [datetime(2500, 4, 7, 10), datetime(2500, 4, 7, 12)],
        ]
        self.assertEqual(solicitacao_mensal_1.get_datas_solicitadas(), datas)

        solicitacao_mensal_2 = self.criar_solicitacao(
            data_inicio=data_base,
            data_fim=adicionar_mes(data_base + timedelta(-1), 2),
            hora_inicio=time(8),
            hora_fim=time(10),
            recorrencia=SolicitacaoReservaSala.RECORRENCIA_MENSALMENTE,
            recorrencia_terca=True,
            recorrencia_quinta=True,
            recorrencia_sabado=True,
            recorrencia_domingo=True,
        )
        # sábado                                               domingo
        datas = [
            [datetime(2500, 1, 2, 8), datetime(2500, 1, 2, 10)],
            [datetime(2500, 1, 3, 8), datetime(2500, 1, 3, 10)],
            # terça                                                quinta
            [datetime(2500, 1, 5, 8), datetime(2500, 1, 5, 10)],
            [datetime(2500, 1, 7, 8), datetime(2500, 1, 7, 10)],
            # terça                                               quinta
            [datetime(2500, 2, 2, 8), datetime(2500, 2, 2, 10)],
            [datetime(2500, 2, 4, 8), datetime(2500, 2, 4, 10)],
            # terça                                                quinta
            [datetime(2500, 2, 6, 8), datetime(2500, 2, 6, 10)],
            [datetime(2500, 2, 7, 8), datetime(2500, 2, 7, 10)],
        ]
        self.assertEqual(solicitacao_mensal_2.get_datas_solicitadas(), datas)


class SalaTestCase(AgendamentoSalaBaseTestCase):
    def get_dados(self):
        return dict(nome=self.campus_a_suap.id, predio=self.predio_agendavel.id, avaliadores_de_agendamentos=[self.servidor_c.id])

    @prevent_logging_errors()
    def test_listar(self):
        """
        1. Só deve aparecer o link para solicitar reserva se a sala for agendavel
        """
        url = '/admin/comum/sala/'
        self.verificar_perfil_status(url, perfis_corretos=[GRUPO_SERVIDOR])

        # Sala inativa
        sala_id = self.sala_inativa.id
        self.verificar_perfil_not_contains(url + '?id={:d}'.format(sala_id), text='href="/comum/sala/solicitar_reserva/{:d}/"'.format(sala_id), perfis_corretos=[GRUPO_SERVIDOR])
        self.verificar_perfil_contains(url + '?id={:d}'.format(sala_id), text='Inativa', perfis_corretos=[GRUPO_SERVIDOR])

        # Sala não agendável
        sala_id = self.sala_nao_agendavel_a.id
        self.verificar_perfil_not_contains(url + '?id={:d}'.format(sala_id), text='href="/comum/sala/solicitar_reserva/{:d}/"'.format(sala_id), perfis_corretos=[GRUPO_SERVIDOR])
        self.verificar_perfil_contains(url + '?id={:d}'.format(sala_id), text='Não é agendável', perfis_corretos=[GRUPO_SERVIDOR])

        # Sala sem avaliador
        sala_id = self.sala_sem_avaliadores.id
        self.verificar_perfil_not_contains(url + '?id={:d}'.format(sala_id), text='href="/comum/sala/solicitar_reserva/{:d}/"'.format(sala_id), perfis_corretos=[GRUPO_SERVIDOR])
        self.verificar_perfil_contains(url + '?id={:d}'.format(sala_id), text='Não possui avaliador', perfis_corretos=[GRUPO_SERVIDOR])

        # Sala agendável
        sala_id = self.sala_agendavel_a.id
        self.verificar_perfil_contains(url + '?id={:d}'.format(sala_id), text='href="/comum/sala/solicitar_reserva/{:d}/"'.format(sala_id), perfis_corretos=[GRUPO_SERVIDOR])

    @prevent_logging_errors()
    def test_add_remover_grupo_avaliador_sala(self):
        """
        Verifica se ao adicionar/remover avaliador de uma sala está se atribuindo/removendo o grupo "Avaliador de Sala"
        """
        Sala.objects.all().delete()
        grupo_avaliador_sala = Group.objects.get(name=GRUPO_AVALIADOR_SALA)
        url = '/admin/comum/sala/add/'
        dados = self.get_dados()
        dados['avaliadores_de_agendamentos'] = [self.servidor_b.user.id, self.servidor_c.user.id]
        self.servidor_b.user.groups.remove(grupo_avaliador_sala)
        self.servidor_c.user.groups.remove(grupo_avaliador_sala)

        if not 'chaves' in settings.INSTALLED_APPS:
            return

        self.verificar_perfil_submit(url, dados, Sala.objects, perfis_corretos=['Coordenador de Chaves'], success_status_code=302)

        self.assertNotIn(grupo_avaliador_sala, self.servidor_a.user.groups.all())
        self.assertIn(grupo_avaliador_sala, self.servidor_b.user.groups.all())
        self.assertIn(grupo_avaliador_sala, self.servidor_c.user.groups.all())

        dados['avaliadores_de_agendamentos'] = [self.servidor_a.user.id, self.servidor_c.user.id]
        sala = Sala.objects.latest('id')
        self.verificar_perfil_submit(
            '/admin/comum/sala/{:d}/change/'.format(sala.id), dados, Sala.objects, perfis_corretos=['Coordenador de Chaves'], incremento=0, success_status_code=302
        )

        self.assertIn(grupo_avaliador_sala, self.servidor_a.user.groups.all())
        self.assertNotIn(grupo_avaliador_sala, self.servidor_b.user.groups.all())
        self.assertIn(grupo_avaliador_sala, self.servidor_c.user.groups.all())

    def test_get_solicitacoes_reserva_pendentes(self):
        #
        # TESTE SOMENTE COM A DATA
        #
        SolicitacaoReservaSala.objects.all().delete()
        # periodo a ser verificado
        # DIAS:
        # 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25
        # -- -- -- -- -- -- -- -- -- 10 <> <> <> <> <> <> <> <> <> 20 -- -- -- -- -- COMPARAÇÃO
        data_inicio = (datetime.now() + timedelta(10)).date()
        data_fim = (datetime.now() + timedelta(20)).date()

        # solicitação com periodo igual ao da verificação
        # -- -- -- -- -- -- -- -- -- 10 <> <> <> <> <> <> <> <> <> 20 -- -- -- -- -- COMPARAÇÃO
        # -- -- -- -- -- -- -- -- -- 10 <> <> <> <> <> <> <> <> <> 20 -- -- -- -- --
        self.criar_solicitacao(data_inicio=data_inicio, data_fim=data_fim)
        self.assertEqual(self.sala_agendavel_a.get_solicitacoes_reserva_pendentes(data_inicio, data_fim).count(), 1)
        # solicitação com periodo igual ao da verificação
        # -- -- -- -- -- -- -- -- -- 10 <> <> <> <> <> <> <> <> <> 20 -- -- -- -- -- COMPARAÇÃO
        # -- -- -- -- -- -- -- -- -- 10 <> <> <> <> <> <> <> <> <> 20 -- -- -- -- --
        self.criar_solicitacao(data_inicio=data_inicio, data_fim=data_fim)
        self.assertEqual(self.sala_agendavel_a.get_solicitacoes_reserva_pendentes(data_inicio, data_fim).count(), 2)

        # solicitação com periodo com data inicial anterior
        # -- -- -- -- -- -- -- -- -- 10 <> <> <> <> <> <> <> <> <> 20 -- -- -- -- -- COMPARAÇÃO
        # -- -- -- -- 05 <> <> <> <> <> <> <> <> <> <> <> <> <> <> 20 -- -- -- -- --
        self.criar_solicitacao(data_inicio=data_inicio + timedelta(-5), data_fim=data_fim)
        self.assertEqual(self.sala_agendavel_a.get_solicitacoes_reserva_pendentes(data_inicio, data_fim).count(), 3)

        # solicitação com periodo com data inicial posterior
        # -- -- -- -- -- -- -- -- -- 10 <> <> <> <> <> <> <> <> <> 20 -- -- -- -- -- COMPARAÇÃO
        # -- -- -- -- -- -- -- -- -- -- -- -- -- -- 15 <> <> <> <> 20 -- -- -- -- --
        self.criar_solicitacao(data_inicio=data_inicio + timedelta(5), data_fim=data_fim)
        self.assertEqual(self.sala_agendavel_a.get_solicitacoes_reserva_pendentes(data_inicio, data_fim).count(), 4)

        # solicitação com periodo com data final posterior
        # -- -- -- -- -- -- -- -- -- 10 <> <> <> <> <> <> <> <> <> 20 -- -- -- -- -- COMPARAÇÃO
        # -- -- -- -- -- -- -- -- -- 10 <> <> <> <> <> <> <> <> <> <> <> <> <> <> 25
        self.criar_solicitacao(data_inicio=data_inicio, data_fim=data_fim + timedelta(5))
        self.assertEqual(self.sala_agendavel_a.get_solicitacoes_reserva_pendentes(data_inicio, data_fim).count(), 5)

        # solicitação com periodo com data final anterior
        # -- -- -- -- -- -- -- -- -- 10 <> <> <> <> <> <> <> <> <> 20 -- -- -- -- -- COMPARAÇÃO
        # -- -- -- -- -- -- -- -- -- 10 <> <> <> <> 15 -- -- -- -- -- -- -- -- -- --
        self.criar_solicitacao(data_inicio=data_inicio, data_fim=data_fim + timedelta(-5))
        self.assertEqual(self.sala_agendavel_a.get_solicitacoes_reserva_pendentes(data_inicio, data_fim).count(), 6)

        # solicitação com periodo que está contido no periodo da verificação
        # -- -- -- -- -- -- -- -- -- 10 <> <> <> <> <> <> <> <> <> 20 -- -- -- -- -- COMPARAÇÃO
        # -- -- -- -- -- -- -- -- -- -- 11 <> <> <> <> <> <> <> 19 -- -- -- -- -- --
        self.criar_solicitacao(data_inicio=data_inicio + timedelta(1), data_fim=data_fim + timedelta(-1))
        self.assertEqual(self.sala_agendavel_a.get_solicitacoes_reserva_pendentes(data_inicio, data_fim).count(), 7)

        # solicitação com periodo que contém o periodo da verificação
        # -- -- -- -- -- -- -- -- -- 10 <> <> <> <> <> <> <> <> <> 20 -- -- -- -- -- COMPARAÇÃO
        # -- -- -- -- 05 <> <> <> <> <> <> <> <> <> <> <> <> <> <> <> <> <> <> <> 25
        self.criar_solicitacao(data_inicio=data_inicio + timedelta(-5), data_fim=data_fim + timedelta(5))
        self.assertEqual(self.sala_agendavel_a.get_solicitacoes_reserva_pendentes(data_inicio, data_fim).count(), 8)

        # solicitação com periodo fora do da verificação, logo depois
        # -- -- -- -- -- -- -- -- -- 10 <> <> <> <> <> <> <> <> <> 20 -- -- -- -- -- COMPARAÇÃO
        # -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 21 <> <> <> 25
        self.criar_solicitacao(data_inicio=data_fim + timedelta(1), data_fim=data_fim + timedelta(5))
        self.assertEqual(self.sala_agendavel_a.get_solicitacoes_reserva_pendentes(data_inicio, data_fim).count(), 8)

        # solicitação com periodo fora do da verificação, depois
        # -- -- -- -- -- -- -- -- -- 10 <> <> <> <> <> <> <> <> <> 20 -- -- -- -- -- COMPARAÇÃO
        # -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 22 <> <> 25
        self.criar_solicitacao(data_inicio=data_fim + timedelta(2), data_fim=data_fim + timedelta(5))
        self.assertEqual(self.sala_agendavel_a.get_solicitacoes_reserva_pendentes(data_inicio, data_fim).count(), 8)

        # solicitação com periodo fora do da verificação, antes
        # -- -- -- -- -- -- -- -- -- 10 <> <> <> <> <> <> <> <> <> 20 -- -- -- -- -- COMPARAÇÃO
        # -- -- -- -- 05 <> <> 08 -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
        self.criar_solicitacao(data_inicio=data_inicio + timedelta(-5), data_fim=data_inicio + timedelta(-2))
        self.assertEqual(self.sala_agendavel_a.get_solicitacoes_reserva_pendentes(data_inicio, data_fim).count(), 8)

        # solicitação com periodo fora do da verificação, log antes
        # -- -- -- -- -- -- -- -- -- 10 <> <> <> <> <> <> <> <> <> 20 -- -- -- -- -- COMPARAÇÃO
        # -- -- -- -- 05 <> <> <> 09 -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
        self.criar_solicitacao(data_inicio=data_inicio + timedelta(-5), data_fim=data_inicio + timedelta(-1))
        self.assertEqual(self.sala_agendavel_a.get_solicitacoes_reserva_pendentes(data_inicio, data_fim).count(), 8)

        #
        # TESTE SOMENTE COM A DATA E HORA
        #
        SolicitacaoReservaSala.objects.all().delete()
        # periodo a ser verificado
        # HORAS:
        # 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24
        # -- -- -- -- -- -- -- 08 <> 10 -- -- -- -- -- -- -- -- -- -- -- -- -- -- COMPARAÇÃO
        data_inicio = (datetime.now() + timedelta(10)).date()
        data_fim = (datetime.now() + timedelta(10)).date()
        hora_inicio = time(8)
        hora_fim = time(10)

        # solicitação com periodo igual ao da verificação
        # -- -- -- -- -- -- -- 08 <> 10 -- -- -- -- -- -- -- -- -- -- -- -- -- -- COMPARAÇÃO
        # -- -- -- -- -- -- -- 08 <> 10 -- -- -- -- -- -- -- -- -- -- -- -- -- --
        self.criar_solicitacao(data_inicio=data_inicio, data_fim=data_fim, hora_inicio=hora_inicio, hora_fim=hora_fim)
        self.assertEqual(self.sala_agendavel_a.get_solicitacoes_reserva_pendentes(data_inicio, data_fim, hora_inicio=hora_inicio, hora_fim=hora_fim).count(), 1)
        # solicitação com periodo igual ao da verificação
        # -- -- -- -- -- -- -- 08 <> 10 -- -- -- -- -- -- -- -- -- -- -- -- -- -- COMPARAÇÃO
        # -- -- -- -- -- -- -- 08 <> 10 -- -- -- -- -- -- -- -- -- -- -- -- -- --
        self.criar_solicitacao(data_inicio=data_inicio, data_fim=data_fim, hora_inicio=hora_inicio, hora_fim=hora_fim)
        self.assertEqual(self.sala_agendavel_a.get_solicitacoes_reserva_pendentes(data_inicio, data_fim, hora_inicio=hora_inicio, hora_fim=hora_fim).count(), 2)

        # solicitação com periodo com hora inicial anterior
        # -- -- -- -- -- -- -- 08 <> 10 -- -- -- -- -- -- -- -- -- -- -- -- -- -- COMPARAÇÃO
        # -- -- -- -- -- -- 07 <> <> 10 -- -- -- -- -- -- -- -- -- -- -- -- -- --
        self.criar_solicitacao(data_inicio=data_inicio, data_fim=data_fim, hora_inicio=time(7), hora_fim=hora_fim)
        self.assertEqual(self.sala_agendavel_a.get_solicitacoes_reserva_pendentes(data_inicio, data_fim, hora_inicio=hora_inicio, hora_fim=hora_fim).count(), 3)

        # solicitação com periodo com hora final posterior
        # -- -- -- -- -- -- -- 08 <> 10 -- -- -- -- -- -- -- -- -- -- -- -- -- -- COMPARAÇÃO
        # -- -- -- -- -- -- -- 08 <> <> <> 12 -- -- -- -- -- -- -- -- -- -- -- --
        self.criar_solicitacao(data_inicio=data_inicio, data_fim=data_fim, hora_inicio=hora_inicio, hora_fim=time(12))
        self.assertEqual(self.sala_agendavel_a.get_solicitacoes_reserva_pendentes(data_inicio, data_fim, hora_inicio=hora_inicio, hora_fim=hora_fim).count(), 4)

        # solicitação com periodo que está contido no periodo da verificação
        # -- -- -- -- -- -- -- 08 <> 10 -- -- -- -- -- -- -- -- -- -- -- -- -- -- COMPARAÇÃO
        # -- -- -- -- -- -- -- -8<>9-- -- -- -- -- -- -- -- -- -- -- -- -- -- --
        self.criar_solicitacao(data_inicio=data_inicio, data_fim=data_fim, hora_inicio=time(8, 30), hora_fim=time(9, 30))
        self.assertEqual(self.sala_agendavel_a.get_solicitacoes_reserva_pendentes(data_inicio, data_fim, hora_inicio=hora_inicio, hora_fim=hora_fim).count(), 5)

        # solicitação com periodo que contém o periodo da verificação
        # -- -- -- -- -- -- -- 08 <> 10 -- -- -- -- -- -- -- -- -- -- -- -- -- -- COMPARAÇÃO
        # -- -- -- -- -- -- 07 <> <> <> <> 12 -- -- -- -- -- -- -- -- -- -- -- --
        self.criar_solicitacao(data_inicio=data_inicio, data_fim=data_fim, hora_inicio=time(7), hora_fim=time(12))
        self.assertEqual(self.sala_agendavel_a.get_solicitacoes_reserva_pendentes(data_inicio, data_fim, hora_inicio=hora_inicio, hora_fim=hora_fim).count(), 6)

        # solicitação com periodo fora do da verificação, depois
        # -- -- -- -- -- -- -- 08 <> 10 -- -- -- -- -- -- -- -- -- -- -- -- -- -- COMPARAÇÃO
        # -- -- -- -- -- -- -- -- -- -10<> 12 -- -- -- -- -- -- -- -- -- -- -- --
        self.criar_solicitacao(data_inicio=data_inicio, data_fim=data_fim, hora_inicio=time(10, 30), hora_fim=time(12))
        self.assertEqual(self.sala_agendavel_a.get_solicitacoes_reserva_pendentes(data_inicio, data_fim, hora_inicio=hora_inicio, hora_fim=hora_fim).count(), 6)

        # solicitação com periodo fora do da verificação, logo depois
        # -- -- -- -- -- -- -- 08 <> 10 -- -- -- -- -- -- -- -- -- -- -- -- -- -- COMPARAÇÃO
        # -- -- -- -- -- -- -- -- -- 10 <> 12 -- -- -- -- -- -- -- -- -- -- -- --
        self.criar_solicitacao(data_inicio=data_inicio, data_fim=data_fim, hora_inicio=time(10), hora_fim=time(12))
        self.assertEqual(self.sala_agendavel_a.get_solicitacoes_reserva_pendentes(data_inicio, data_fim, hora_inicio=hora_inicio, hora_fim=hora_fim).count(), 6)

        # solicitação com periodo fora do da verificação, antes
        # -- -- -- -- -- -- -- 08 <> 10 -- -- -- -- -- -- -- -- -- -- -- -- -- -- COMPARAÇÃO
        # -- -- -- -- 05 06 -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
        self.criar_solicitacao(data_inicio=data_inicio, data_fim=data_fim, hora_inicio=time(5), hora_fim=time(6))
        self.assertEqual(self.sala_agendavel_a.get_solicitacoes_reserva_pendentes(data_inicio, data_fim, hora_inicio=hora_inicio, hora_fim=hora_fim).count(), 6)

        # solicitação com periodo fora do da verificação, logo antes
        # -- -- -- -- -- -- -- 08 <> 10 -- -- -- -- -- -- -- -- -- -- -- -- -- -- COMPARAÇÃO
        # -- -- -- -- 05 <> -7 -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
        self.criar_solicitacao(data_inicio=data_inicio, data_fim=data_fim, hora_inicio=time(5), hora_fim=time(7, 59))
        self.assertEqual(self.sala_agendavel_a.get_solicitacoes_reserva_pendentes(data_inicio, data_fim, hora_inicio=hora_inicio, hora_fim=hora_fim).count(), 6)


class ReservaSalaTestCase(AgendamentoSalaBaseTestCase):
    def setUp(self):
        super().setUp()
        # Criando a base para teste
        SolicitacaoReservaSala.objects.all().delete()
        data = datetime.now().date() + timedelta(10)
        # SALA A
        # -- -- -- -- -- -- -- -- -- 10 <> 12 -- -- -- -- -- -- -- -- -- -- -- --
        self.solicitacao_exibida_a = self.criar_solicitacao(solicitante=self.servidor_b.user, data_inicio=data, data_fim=data, hora_inicio=time(10), hora_fim=time(12))
        # -- -- -- -- -- -- -- 08 <> 10 -- -- -- -- -- -- -- -- -- -- -- -- -- --
        self.solicitacao_deferida_a = self.criar_solicitacao(
            status=SolicitacaoReservaSala.STATUS_DEFERIDA, solicitante=self.servidor_b.user, data_inicio=data, data_fim=data, hora_inicio=time(8), hora_fim=time(10)
        )
        # -- -- -- -- -- -- -- -- -- -- 11 <> <> 14 -- -- -- -- -- -- -- -- -- --
        self.solicitacao_conflitante_a = self.criar_solicitacao(solicitante=self.servidor_b.user, data_inicio=data, data_fim=data, hora_inicio=time(11), hora_fim=time(14))
        # SALA B
        # -- -- -- -- -- -- -- -- -- 10 <> 12 -- -- -- -- -- -- -- -- -- -- -- --
        self.solicitacao_exibida_b = self.criar_solicitacao(sala=self.sala_agendavel_b, data_inicio=data, data_fim=data, hora_inicio=time(10), hora_fim=time(12))
        # -- -- -- -- -- -- -- 08 <> 10 -- -- -- -- -- -- -- -- -- -- -- -- -- --
        self.solicitacao_deferida_b = self.criar_solicitacao(
            status=SolicitacaoReservaSala.STATUS_DEFERIDA, sala=self.sala_agendavel_b, data_inicio=data, data_fim=data, hora_inicio=time(8), hora_fim=time(10)
        )
        # -- -- -- -- -- -- -- 08 <> <> <> <> <> 14 -- -- -- -- -- -- -- -- -- --
        self.solicitacao_conflitante_b = self.criar_solicitacao(sala=self.sala_agendavel_b, data_inicio=data, data_fim=data, hora_inicio=time(8), hora_fim=time(14))

    @prevent_logging_errors()
    def test_desaparecer_painel_notificacao(self):
        """
        1. Só o perfil de Servidor e que é avaliador de sala pode ver o painel
        2. UC 04 - Segunda pós-condição: É excluído no Painel de Notificação do avaliador o aviso de que existem agendamentos pendentes de avaliação.
        3. UC 04 - RN2: O aviso de que existem agendamentos pendentes de avaliação disponível no Painel de Notificação só será excluído se não existir mais solicitações de reservas a serem avaliadas.
        """
        SolicitacaoReservaSala.objects.all().delete()
        self.solicitacao_b.save()
        self.solicitacao_sala_b.save()
        texto_sala = 'Solicitação de Sala'
        # Como o servidor_a é avaliador da sala_a ele vê a solicitacao_b
        self.verificar_perfil_contains('/', text=texto_sala, perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR])
        self.solicitacao_b.status = SolicitacaoReservaSala.STATUS_DEFERIDA
        self.solicitacao_b.save()
        self.verificar_perfil_not_contains('/', text=texto_sala, perfis_corretos=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR])

        self.client.logout()
        self.client.login(user=self.servidor_b.user)
        # Como o servidor_b é avaliador da sala_b ele vê a solicitacao_sala_b
        self.verificar_perfil_contains('/', text=texto_sala, perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR], user=self.servidor_b.user)
        self.solicitacao_sala_b.status = SolicitacaoReservaSala.STATUS_DEFERIDA
        self.solicitacao_sala_b.save()
        self.verificar_perfil_not_contains('/', text=texto_sala, perfis_corretos=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR], user=self.servidor_b.user)

    @prevent_logging_errors()
    def test_listar(self):
        """
        1. Só o perfil de Servidor e que é avaliador de sala pode a listagem
        2. Só pode ver solicitações de reserva de salas que ele é avaliador
        3. Só deve listar as solicitações que não tem conflito de horários com outras
        """
        url = 'href="/comum/sala/ver_solicitacao/{:d}/"'
        # Verificação da aba "Qualquer"
        url_base = '/admin/comum/solicitacaoreservasala/'
        # solicitações da sala que o usuário é avaliador
        self.verificar_perfil_contains(url_base, text=url.format(self.solicitacao_exibida_a.id), perfis_corretos=[GRUPO_AVALIADOR_SALA], error_status_code=403)
        self.verificar_perfil_contains(url_base, text=url.format(self.solicitacao_deferida_a.id), perfis_corretos=[GRUPO_AVALIADOR_SALA], error_status_code=403)
        self.verificar_perfil_contains(url_base, text=url.format(self.solicitacao_conflitante_a.id), perfis_corretos=[GRUPO_AVALIADOR_SALA], error_status_code=403)
        # solicitações de sala que o usuário não é avaliador mas é o solicitante
        # verifica se tem o link para ver a solicitação
        self.verificar_perfil_contains(url_base, text=url.format(self.solicitacao_exibida_b.id), perfis_corretos=[GRUPO_AVALIADOR_SALA], error_status_code=403)
        self.verificar_perfil_contains(url_base, text=url.format(self.solicitacao_deferida_b.id), perfis_corretos=[GRUPO_AVALIADOR_SALA], error_status_code=403)
        self.verificar_perfil_contains(url_base, text=url.format(self.solicitacao_conflitante_b.id), perfis_corretos=[GRUPO_AVALIADOR_SALA], error_status_code=403)
        # verifica se mostra a sala
        self.verificar_perfil_contains(url_base, text=self.solicitacao_exibida_b.sala.nome, perfis_corretos=[GRUPO_AVALIADOR_SALA], error_status_code=403)
        self.verificar_perfil_contains(url_base, text=self.solicitacao_deferida_b.sala.nome, perfis_corretos=[GRUPO_AVALIADOR_SALA], error_status_code=403)
        self.verificar_perfil_contains(url_base, text=self.solicitacao_conflitante_b.sala.nome, perfis_corretos=[GRUPO_AVALIADOR_SALA], error_status_code=403)

        # Verificação da aba "Solicitações a avaliar"
        url_base = '/admin/comum/solicitacaoreservasala/?tab=tab_solicitacoes_a_avaliar'
        # solicitações do usuário
        self.verificar_perfil_contains(url_base, text=url.format(self.solicitacao_exibida_a.id), perfis_corretos=[GRUPO_AVALIADOR_SALA], error_status_code=403)
        self.verificar_perfil_not_contains(url_base, text=url.format(self.solicitacao_deferida_a.id), perfis_corretos=[GRUPO_AVALIADOR_SALA], success_status_code=403)
        self.verificar_perfil_contains(url_base, text=url.format(self.solicitacao_conflitante_a.id), perfis_corretos=[GRUPO_AVALIADOR_SALA], error_status_code=403)
        # solicitações de outro usuário
        self.verificar_perfil_not_contains(url_base, text=url.format(self.solicitacao_exibida_b.id), perfis_corretos=[GRUPO_AVALIADOR_SALA], success_status_code=403)
        self.verificar_perfil_not_contains(url_base, text=url.format(self.solicitacao_deferida_b.id), perfis_corretos=[GRUPO_AVALIADOR_SALA], success_status_code=403)
        self.verificar_perfil_not_contains(url_base, text=url.format(self.solicitacao_conflitante_b.id), perfis_corretos=[GRUPO_AVALIADOR_SALA], success_status_code=403)

    @prevent_logging_errors()
    def test_deferir_solicitacao(self):
        """
        1. Só o perfil de Servidor avaliador de sala deferir solicitação
        2. O usuário corrente só pode avaliar solicitações de sala que ele é avaliador
        3. UC 04 - RN1: essa opção só estará disponível para avaliador e se a data final da requisição for menor ou igual a data atual e a requisição não tenha sido avaliada.
        4. UC 04 - Primeira pós-condição: É enviado um e-mail para os solicitantes de reserva informando que a reserva foi avaliada;
        """

        def desmodificar(solicitacao):
            solicitacao.data_avaliacao = None
            solicitacao.avaliador = None
            solicitacao.observacao_avaliador = ""
            solicitacao.status = SolicitacaoReservaSala.STATUS_AGUARDANDO_AVALIACAO
            solicitacao.save()
            solicitacao.reservasala_set.all().delete()

        def modificou(solicitacao):
            solicitacao = SolicitacaoReservaSala.objects.get(id=solicitacao.id)
            return solicitacao.status == SolicitacaoReservaSala.STATUS_DEFERIDA and solicitacao.reservasala_set.all().exists()

        # usuario_b fez a solicitação solicitacao_b
        url_base = '/comum/sala/ver_solicitacao/{:d}/'.format(self.solicitacao_exibida_a.id)
        url = '/comum/sala/avaliar_solicitacao/{:d}/'.format(self.solicitacao_exibida_a.id)
        dados = {'status': SolicitacaoReservaSala.STATUS_DEFERIDA, 'observacao_avaliador': 'teste'}
        self.solicitacao_exibida_a.interessados_vinculos.add(self.servidor_c.get_vinculo())
        # usuario_b não é o avaliador da sala
        self.client.logout()
        self.client.login(user=self.servidor_b.user)
        # Verifica se existe o link para avaliação
        # UC 04 - RN1: essa opção só estará disponível para avaliador e se a data final da requisição for menor ou igual a data atual e a requisição não tenha sido avaliada.
        self.verificar_perfil_not_contains(
            url_base, text='href="{}"'.format(url), perfis_corretos=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR], success_status_code=403, user=self.servidor_b.user
        )
        # Avalia a solicitação
        self.verificar_perfil_status(url, perfis_errados=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR], user=self.servidor_b.user)
        self.verificar_perfil_submit(
            url,
            dados,
            SolicitacaoReservaSala.objects,
            perfis_errados=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR],
            after_submit=lambda: desmodificar(self.solicitacao_exibida_a),
            modificou=lambda: modificou(self.solicitacao_exibida_a),
            user=self.servidor_b.user,
        )

        # usuario_a é o avaliador da sala
        self.client.logout()
        self.client.login(user=self.servidor_a.user)
        # Verifica se existe o link para avaliação
        self.verificar_perfil_contains(url_base, text='href="{}"'.format(url), perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR], error_status_code=403)
        # Avalia a solicitação
        self.verificar_perfil_status(url, perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR])
        self.verificar_perfil_submit(
            url,
            dados,
            SolicitacaoReservaSala.objects,
            perfis_corretos=[GRUPO_AVALIADOR_SALA],
            perfis_errados=[GRUPO_SERVIDOR],
            success_status_code=302,
            incremento=0,
            after_submit=lambda: desmodificar(self.solicitacao_exibida_a),
            modificou=lambda: modificou(self.solicitacao_exibida_a),
        )
        # UC 04 - Primeira pós-condição: É enviado um e-mail para os solicitantes de reserva informando que a reserva foi avaliada;
        requisitante_email = self.servidor_b.email
        interessado_email = self.servidor_c.email
        # Não envia para o avaliador, já que foi ele que executou a ação
        self.verificar_envio_email([requisitante_email, interessado_email], '[SUAP] Reservas de Salas: Solicitação Deferida')

        # Avaliar Solicitação
        self.verificar_perfil_submit(
            url, dados, SolicitacaoReservaSala.objects, perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR], success_status_code=302, incremento=0
        )

        # Não deve permirit Avaliar Solicitação já que já está reservado o horário
        data_inicio = self.solicitacao_exibida_a.data_inicio
        data_fim = self.solicitacao_exibida_a.data_fim
        hora_inicio = self.solicitacao_exibida_a.hora_inicio
        hora_fim = self.solicitacao_exibida_a.hora_fim
        self.solicitacao_exibida_a2 = self.criar_solicitacao(
            solicitante=self.servidor_b.user, data_inicio=data_inicio, data_fim=data_fim, hora_inicio=hora_inicio, hora_fim=hora_fim
        )
        url = '/comum/sala/avaliar_solicitacao/{:d}/'.format(self.solicitacao_exibida_a2.id)
        self.verificar_perfil_submit(
            url,
            dados,
            SolicitacaoReservaSala.objects,
            perfis_corretos=[],
            perfis_errados=[GRUPO_SERVIDOR],
            incremento=0,
            contains_text='Sala já está reservada para a data e hora especificadas.',
        )

        self.verificar_perfil_submit(
            url,
            dados,
            SolicitacaoReservaSala.objects,
            perfis_corretos=[],
            perfis_errados=[GRUPO_AVALIADOR_SALA],
            incremento=0,
            error_status_code=200,
            contains_text='Sala já está reservada para a data e hora especificadas.',
        )

    @prevent_logging_errors()
    def test_indeferir_solicitacao(self):
        """
        1. Só o perfil de Servidor avaliador de sala indeferir solicitação
        2. O usuário corrente só pode avaliar solicitações de sala que ele é avaliador
        3. UC 04 - RN1: essa opção só estará disponível para avaliador e se a data final da requisição for menor ou igual a data atual e a requisição não tenha sido avaliada.
        4. UC 04 - Primeira pós-condição: É enviado um e-mail para os solicitantes de reserva informando que a reserva foi avaliada;
        """

        def desmodificar(solicitacao):
            solicitacao.data_avaliacao = None
            solicitacao.avaliador = None
            solicitacao.observacao_avaliador = ""
            solicitacao.status = SolicitacaoReservaSala.STATUS_AGUARDANDO_AVALIACAO
            solicitacao.save()
            solicitacao.reservasala_set.all().delete()

        def modificou(solicitacao):
            solicitacao = SolicitacaoReservaSala.objects.get(id=solicitacao.id)
            return solicitacao.status == SolicitacaoReservaSala.STATUS_INDEFERIDA and not solicitacao.reservasala_set.all().exists()

        # usuario_b fez a solicitação solicitacao_b
        url_base = '/comum/sala/ver_solicitacao/{:d}/'.format(self.solicitacao_exibida_a.id)
        url = '/comum/sala/avaliar_solicitacao/{:d}/'.format(self.solicitacao_exibida_a.id)
        dados = {'status': SolicitacaoReservaSala.STATUS_INDEFERIDA, 'observacao_avaliador': 'teste'}
        self.solicitacao_exibida_a.interessados_vinculos.add(self.servidor_c.get_vinculo())
        # usuario_b não é o avaliador da sala
        self.client.logout()
        self.client.login(user=self.servidor_b.user)
        # Verifica se existe o link para avaliação
        # UC 04 - RN1: essa opção só estará disponível para avaliador e se a data final da requisição for menor ou igual a data atual e a requisição não tenha sido avaliada.
        self.verificar_perfil_not_contains(
            url_base, text='href="{}"'.format(url), perfis_corretos=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR], success_status_code=403, user=self.servidor_b.user
        )
        # Avalia a solicitação
        self.verificar_perfil_status(url, perfis_errados=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR], user=self.servidor_b.user)
        self.verificar_perfil_submit(
            url,
            dados,
            SolicitacaoReservaSala.objects,
            perfis_errados=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR],
            after_submit=lambda: desmodificar(self.solicitacao_exibida_a),
            modificou=lambda: modificou(self.solicitacao_exibida_a),
            user=self.servidor_b.user,
        )

        # usuario_a é o avaliador da sala
        self.client.logout()
        self.client.login(user=self.servidor_a.user)

        # Verifica se existe o link para avaliação
        self.verificar_perfil_contains(url_base, text='href="{}"'.format(url), perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR], error_status_code=403)
        # Avalia a solicitação
        self.verificar_perfil_status(url, perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR])
        self.verificar_perfil_submit(
            url,
            dados,
            SolicitacaoReservaSala.objects,
            perfis_corretos=[GRUPO_AVALIADOR_SALA],
            perfis_errados=[GRUPO_SERVIDOR],
            success_status_code=302,
            incremento=0,
            after_submit=lambda: desmodificar(self.solicitacao_exibida_a),
            modificou=lambda: modificou(self.solicitacao_exibida_a),
        )
        # UC 04 - Primeira pós-condição: É enviado um e-mail para os solicitantes de reserva informando que a reserva foi avaliada;
        requisitante_email = self.servidor_b.email
        interessado_email = self.servidor_c.email
        # Não envia para o avaliador, já que foi ele que executou a ação
        self.verificar_envio_email([requisitante_email, interessado_email], '[SUAP] Reservas de Salas: Solicitação Indeferida')

        # Deferindo uma solicitação que terá conflito de horário com a solicitação a ser indeferida
        # Criando a base para teste
        self.criar_solicitacao(
            status=SolicitacaoReservaSala.STATUS_DEFERIDA,
            solicitante=self.servidor_b.user,
            data_inicio=self.solicitacao_conflitante_a.data_inicio,
            data_fim=self.solicitacao_conflitante_a.data_fim,
            hora_inicio=self.solicitacao_conflitante_a.hora_inicio,
            hora_fim=self.solicitacao_conflitante_a.hora_fim,
        )

        url_base = '/comum/sala/ver_solicitacao/{:d}/'.format(self.solicitacao_conflitante_a.id)
        url = '/comum/sala/avaliar_solicitacao/{:d}/'.format(self.solicitacao_conflitante_a.id)

        # Verifica se existe o link para avaliação
        self.verificar_perfil_contains(url_base, text='href="{}"'.format(url), perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR], error_status_code=403)
        # Avalia a solicitação
        self.verificar_perfil_status(url, perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR])
        self.verificar_perfil_submit(
            url,
            dados,
            SolicitacaoReservaSala.objects,
            perfis_corretos=[GRUPO_AVALIADOR_SALA],
            perfis_errados=[GRUPO_SERVIDOR],
            success_status_code=302,
            incremento=0,
            after_submit=lambda: desmodificar(self.solicitacao_conflitante_a),
            modificou=lambda: modificou(self.solicitacao_conflitante_a),
        )
        # UC 04 - Primeira pós-condição: É enviado um e-mail para os solicitantes de reserva informando que a reserva foi avaliada;
        requisitante_email = self.servidor_b.email
        # Não envia para o avaliador, já que foi ele que executou a ação
        self.verificar_envio_email([requisitante_email], '[SUAP] Reservas de Salas: Solicitação Indeferida')


class IndisponibilizacaoSalaTestCase(AgendamentoSalaBaseTestCase):
    def setUp(self):
        super().setUp()
        # Criando a base para teste
        SolicitacaoReservaSala.objects.all().delete()
        ReservaSala.objects.all().delete()
        data = datetime.now()
        # SALA A
        self.indisponibilizacao_futura = self.criar_indisponibilizacao(data_inicio=data + timedelta(2), data_fim=data + timedelta(8))
        self.indisponibilizacao_passada = self.criar_indisponibilizacao(data_inicio=data + timedelta(-8), data_fim=data + timedelta(-2))
        self.indisponibilizacao_em_andamento = self.criar_indisponibilizacao(data_inicio=data + timedelta(-2), data_fim=data + timedelta(2))

        # SALA B
        self.indisponibilizacao_futura_b = self.criar_indisponibilizacao(sala=self.sala_agendavel_b, data_inicio=data + timedelta(2), data_fim=data + timedelta(8))
        self.indisponibilizacao_passada_b = self.criar_indisponibilizacao(sala=self.sala_agendavel_b, data_inicio=data + timedelta(-8), data_fim=data + timedelta(-2))
        self.indisponibilizacao_em_andamento_b = self.criar_indisponibilizacao(sala=self.sala_agendavel_b, data_inicio=data + timedelta(-2), data_fim=data + timedelta(2))
        return locals()

    def criar_indisponibilizacao(self, sala=None, **params):
        """
        Cria uma indisponibilizacao com os valores padrões se não for passado parâmetro
        """
        if not sala:
            sala = self.sala_agendavel_a

        data_inicio = datetime.now() + timedelta(10)
        data_fim = datetime.now() + timedelta(10)
        init = dict(
            usuario=self.servidor_a.user, data=datetime.now(), sala=sala, justificativa=SolicitacaoReservaSala.RECORRENCIA_EVENTO_UNICO, data_inicio=data_inicio, data_fim=data_fim
        )
        init.update(params)
        indisponibilizacao = IndisponibilizacaoSala.objects.create(**init)
        indisponibilizacao = IndisponibilizacaoSala.objects.get(pk=indisponibilizacao.pk)
        return indisponibilizacao

    def get_dados(self):
        data_inicio = (datetime.now() + timedelta(10)).replace(hour=8, minute=0, second=0, microsecond=0)
        data_fim = (datetime.now() + timedelta(10)).replace(hour=12, minute=0, second=0, microsecond=0)
        hora_inicio = data_inicio.time()
        hora_fim = data_fim.time()
        data_inicio = data_inicio.strftime('%Y-%m-%dT%H:%M:%S')
        data_fim = data_fim.strftime('%Y-%m-%dT%H:%M:%S')
        return dict(
            campus=self.campus_a_suap.id,
            predio=self.predio_agendavel.id,
            sala=self.sala_agendavel_a.id,
            data_inicio=data_inicio,
            hora_inicio=hora_inicio,
            data_fim=data_fim,
            hora_fim=hora_fim,
            justificativa='Contrato para prestacao algum serviço',
        )

    @prevent_logging_errors()
    def test_listar(self):
        """
        1. Só avaliadores podem ver a listagem
        2. Na aba "Em manutenção" só devem aparecer as Indisponibilicações que estão ocorrendo no momento
        """
        url = 'href="/comum/sala/ver_indisponibilizacao/{:d}/"'
        url_base = '/comum/sala/listar_indisponibilizacoes/'
        self.verificar_perfil_status(url_base, perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR])
        self.verificar_perfil_contains(
            url_base, text=url.format(self.indisponibilizacao_futura.id), perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR], error_status_code=403
        )
        self.verificar_perfil_contains(
            url_base, text=url.format(self.indisponibilizacao_passada.id), perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR], error_status_code=403
        )
        self.verificar_perfil_contains(
            url_base, text=url.format(self.indisponibilizacao_em_andamento.id), perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR], error_status_code=403
        )
        # Verificação da aba "qualquer"
        url_base = '/comum/sala/listar_indisponibilizacoes/?tab=qualquer'
        self.verificar_perfil_status(url_base, perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR])
        self.verificar_perfil_contains(
            url_base, text=url.format(self.indisponibilizacao_futura.id), perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR], error_status_code=403
        )
        self.verificar_perfil_contains(
            url_base, text=url.format(self.indisponibilizacao_passada.id), perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR], error_status_code=403
        )
        self.verificar_perfil_contains(
            url_base, text=url.format(self.indisponibilizacao_em_andamento.id), perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR], error_status_code=403
        )
        # Verificação da aba "em_manutencao"
        url_base = '/comum/sala/listar_indisponibilizacoes/?tab=em_manutencao'
        self.verificar_perfil_status(url_base, perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR])
        self.verificar_perfil_not_contains(
            url_base, text=url.format(self.indisponibilizacao_futura.id), perfis_corretos=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR], success_status_code=403
        )
        self.verificar_perfil_not_contains(
            url_base, text=url.format(self.indisponibilizacao_passada.id), perfis_corretos=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR], success_status_code=403
        )
        self.verificar_perfil_contains(
            url_base, text=url.format(self.indisponibilizacao_em_andamento.id), perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR], error_status_code=403
        )

    @prevent_logging_errors()
    def test_ver_botao_registrar_indisponibilizacao(self):
        """
        1. Só avaliadores podem cadastrar indisponibilização
        """
        # Servidor A está logado e é avaliador de sala
        url_base = '/comum/sala/listar_indisponibilizacoes/'
        url = '/comum/sala/registrar_indisponibilizacao/'
        self.verificar_perfil_contains(url_base, text='href="{}"'.format(url), perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR], error_status_code=403)
        self.verificar_perfil_status(url, perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR])

        # Servidor C está logado e não é avaliador de sala, portanto não pode ver
        self.client.logout()
        self.client.login(user=self.servidor_c.user)
        self.verificar_perfil_not_contains(
            url_base, text='href="{}"'.format(url), perfis_corretos=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR], success_status_code=403, user=self.servidor_c.user
        )
        self.verificar_perfil_status(url, perfis_errados=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR], user=self.servidor_c.user)

    @prevent_logging_errors()
    def test_cadastrar(self):
        """
        1. Só avaliadores podem cadastrar indisponibilização
        2. O avaliador só pode cadastrar indisponibilização de sala que ele é avaliador
        """
        IndisponibilizacaoSala.objects.all().delete()
        url = '/comum/sala/registrar_indisponibilizacao/'
        dados = self.get_dados()
        self.verificar_perfil_submit(url, dados, IndisponibilizacaoSala.objects, perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR], success_status_code=302)

        # Só pode cadastrar indisponibilização de sala que ele é avaliador
        dados["sala"] = self.sala_agendavel_b.id
        self.verificar_perfil_submit(url, dados, IndisponibilizacaoSala.objects, perfis_errados=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR])

    @prevent_logging_errors()
    def test_cadastrar_conflito_reserva(self):
        """
        1. Só avaliadores podem cadastrar indisponibilização
        2. UC 03 - RN1: Não deve existir duas agendas de salas na mesma data/hora.
        """
        IndisponibilizacaoSala.objects.all().delete()
        url = '/comum/sala/registrar_indisponibilizacao/'
        dados = self.get_dados()
        self.verificar_perfil_submit(url, dados, IndisponibilizacaoSala.objects, perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR], success_status_code=302)

        # Já existe uma indisponibilização para a mesmadata/hora
        self.verificar_perfil_submit(
            url,
            dados,
            IndisponibilizacaoSala.objects,
            perfis_corretos=[],
            perfis_errados=[GRUPO_SERVIDOR],
            incremento=0,
            contains_text='Sala já está reservada para a data e hora especificadas, exclua antes a reserva.',
        )

        # Já existe uma indisponibilização para a mesmadata/hora
        self.verificar_perfil_submit(
            url,
            dados,
            IndisponibilizacaoSala.objects,
            perfis_corretos=[],
            perfis_errados=[GRUPO_AVALIADOR_SALA],
            incremento=0,
            error_status_code=200,
            contains_text='Sala já está reservada para a data e hora especificadas, exclua antes a reserva.',
        )
        # para outro periodo já pode
        data = (datetime.now() + timedelta(20)).strftime('%Y-%m-%d')
        dados["data_inicio"] = data
        dados["data_fim"] = data
        self.verificar_perfil_submit(
            url,
            dados,
            IndisponibilizacaoSala.objects,
            perfis_corretos=[GRUPO_AVALIADOR_SALA],
            perfis_errados=[GRUPO_SERVIDOR],
            success_status_code=302,
            not_contains_text='Sala já está reservada para a data e hora especificadas, exclua antes a reserva.',
        )

    @prevent_logging_errors()
    def test_cadastrar_conflito_solicitacao(self):
        """
        1. Só avaliadores podem cadastrar indisponibilização
        2. UC 03 - RN2: Requisições de reserva de sala na mesa data/hora será indeferida.
        """
        IndisponibilizacaoSala.objects.all().delete()
        url = '/comum/sala/registrar_indisponibilizacao/'
        dados = self.get_dados()
        data = (datetime.now() + timedelta(20))
        # Pegando a segunda feira
        data = data + timedelta(-data.weekday())
        data_inicio = data.replace(hour=8, minute=0, second=0, microsecond=0)
        data_fim = data_inicio.replace(hour=12)
        # Cadastrando uma solicitação mensal segunda
        self.criar_solicitacao(
            data_inicio=data.date(),
            data_fim=(data + timedelta(120)).date(),
            hora_inicio=dados["hora_inicio"],
            hora_fim=dados["hora_fim"],
            recorrencia=SolicitacaoReservaSala.RECORRENCIA_MENSALMENTE,
            recorrencia_segunda=True,
        )

        # Já existe uma indisponibilização para a mesma data/hora
        dados["data_inicio"] = data_inicio.strftime('%Y-%m-%dT%H:%M:%S')
        dados["data_fim"] = data_fim.strftime('%Y-%m-%dT%H:%M:%S')
        self.verificar_perfil_submit(
            url,
            dados,
            IndisponibilizacaoSala.objects,
            perfis_corretos=[],
            perfis_errados=[GRUPO_SERVIDOR],
            incremento=0,
            contains_text='Existem requisições de reserva para esta sala no período solicitado, indefira antes as requisições.',
        )
        self.verificar_perfil_submit(
            url,
            dados,
            IndisponibilizacaoSala.objects,
            perfis_corretos=[],
            perfis_errados=[GRUPO_AVALIADOR_SALA],
            incremento=0,
            error_status_code=200,
            contains_text='Existem requisições de reserva para esta sala no período solicitado, indefira antes as requisições.',
        )
        # Mas para a próxima segunda não há
        dados["data_inicio"] = (data + timedelta(7)).strftime('%Y-%m-%d')
        dados["data_fim"] = (data + timedelta(7)).strftime('%Y-%m-%d')
        self.verificar_perfil_submit(
            url,
            dados,
            IndisponibilizacaoSala.objects,
            perfis_corretos=[GRUPO_AVALIADOR_SALA],
            perfis_errados=[GRUPO_SERVIDOR],
            success_status_code=302,
            not_contains_text='Existem requisições de reserva para esta sala no período solicitado, indefira antes as requisições.',
        )

    @prevent_logging_errors()
    def test_visualizar(self):
        """
        1. Só avaliadores podem visualizar
        """
        url = '/comum/sala/ver_indisponibilizacao/{:d}/'.format(self.indisponibilizacao_futura.id)
        self.verificar_perfil_status(url, perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR])
        self.verificar_perfil_contains(
            url, text='Visualizar Registro de Indisponibilização', perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR], error_status_code=403
        )
        url = '/comum/sala/ver_indisponibilizacao/{:d}/'.format(self.indisponibilizacao_passada.id)
        self.verificar_perfil_status(url, perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR])
        self.verificar_perfil_contains(
            url, text='Visualizar Registro de Indisponibilização', perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR], error_status_code=403
        )
        url = '/comum/sala/ver_indisponibilizacao/{:d}/'.format(self.indisponibilizacao_em_andamento.id)
        self.verificar_perfil_status(url, perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR])
        self.verificar_perfil_contains(
            url, text='Visualizar Registro de Indisponibilização', perfis_corretos=[GRUPO_AVALIADOR_SALA], perfis_errados=[GRUPO_SERVIDOR], error_status_code=403
        )

    @prevent_logging_errors()
    def test_apagar(self):
        """
        1. Só avaliadores podem remover indisponibilização
        2. Só pode remover as indisponibilizações da sala que ele é avaliador
        3. UC 03 - RN7: Critério para exibição da opção excluir: essa opção só estará disponível se a data final do registro de manutenção for menor que a data atual.
        """
        url_base = '/comum/sala/listar_indisponibilizacoes/'
        url = '/comum/sala/excluir_indisponibilizacao/{:d}/'

        self.verificar_perfil_contains(
            url_base,
            text='href="{}"'.format(url).format(self.indisponibilizacao_futura.id),
            perfis_corretos=[GRUPO_AVALIADOR_SALA],
            perfis_errados=[GRUPO_SERVIDOR],
            error_status_code=403,
        )
        self.verificar_perfil_remover(
            url,
            [self.indisponibilizacao_futura.id, self.indisponibilizacao_futura.id],
            queryset=IndisponibilizacaoSala.objects.all(),
            perfis_corretos=[GRUPO_AVALIADOR_SALA],
            perfis_errados=[GRUPO_SERVIDOR],
            success_status_code=302,
        )

        self.verificar_perfil_contains(
            url_base,
            text='href="{}"'.format(url).format(self.indisponibilizacao_em_andamento.id),
            perfis_corretos=[GRUPO_AVALIADOR_SALA],
            perfis_errados=[GRUPO_SERVIDOR],
            error_status_code=403,
        )
        self.verificar_perfil_remover(
            url,
            [self.indisponibilizacao_em_andamento.id, self.indisponibilizacao_em_andamento.id],
            queryset=IndisponibilizacaoSala.objects.all(),
            perfis_corretos=[GRUPO_AVALIADOR_SALA],
            perfis_errados=[GRUPO_SERVIDOR],
            success_status_code=302,
        )

        # Indisponibilização de sala em que é o avaliador não pode ser removida mas já passou
        self.verificar_perfil_not_contains(
            url_base, text='href="{}"'.format(url).format(self.indisponibilizacao_passada.id), perfis_corretos=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR], success_status_code=403
        )
        self.verificar_perfil_remover(
            url,
            [self.indisponibilizacao_passada.id, self.indisponibilizacao_passada.id],
            queryset=IndisponibilizacaoSala.objects.all(),
            perfis_errados=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR],
            success_status_code=302,
        )

        # Indisponibilização de sala em que não é o avaliador não pode ser removida
        self.verificar_perfil_not_contains(
            url_base, text='href="{}"'.format(url).format(self.indisponibilizacao_futura_b.id), perfis_corretos=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR], success_status_code=403
        )
        self.verificar_perfil_remover(
            url,
            [self.indisponibilizacao_futura_b.id, self.indisponibilizacao_futura_b.id],
            queryset=IndisponibilizacaoSala.objects.all(),
            perfis_errados=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR],
            success_status_code=302,
        )

        self.verificar_perfil_not_contains(
            url_base, text='href="{}"'.format(url).format(self.indisponibilizacao_passada_b.id), perfis_corretos=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR], success_status_code=403
        )
        self.verificar_perfil_remover(
            url,
            [self.indisponibilizacao_passada_b.id, self.indisponibilizacao_passada_b.id],
            queryset=IndisponibilizacaoSala.objects.all(),
            perfis_errados=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR],
            success_status_code=302,
        )

        self.verificar_perfil_not_contains(
            url_base,
            text='href="{}"'.format(url).format(self.indisponibilizacao_em_andamento_b.id),
            perfis_corretos=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR],
            success_status_code=403,
        )
        self.verificar_perfil_remover(
            url,
            [self.indisponibilizacao_em_andamento_b.id, self.indisponibilizacao_em_andamento_b.id],
            queryset=IndisponibilizacaoSala.objects.all(),
            perfis_errados=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR],
            success_status_code=302,
        )


class CancelamentoReservaTestCase(AgendamentoSalaBaseTestCase):
    def setUp(self):
        super().setUp()
        # Criando a base para teste
        SolicitacaoReservaSala.objects.all().delete()
        data = datetime.now().date()
        # data_fim = data + timedelta(days=1)
        # SALA A
        # -- -- -- -- -- -- -- 08 <> 10 -- -- -- -- -- -- -- -- -- -- -- -- -- --
        self.solicitacao_deferida_a = self.criar_solicitacao(
            status=SolicitacaoReservaSala.STATUS_DEFERIDA,
            solicitante=self.servidor_b.user,
            data_inicio=data,
            data_fim=data + timedelta(days=1),
            hora_inicio=time(8),
            hora_fim=time(10),
        )
        self.solicitacao_deferida_a.interessados_vinculos.add(self.servidor_c.get_vinculo())
        self.reserva_solicitacao_a = self.solicitacao_deferida_a.reservasala_set.latest('id')
        # SALA B
        # -- -- -- -- -- -- -- -- -- -- -- 12 <> <> 15 -- -- -- -- -- -- -- -- --
        self.solicitacao_deferida_b = self.criar_solicitacao(
            status=SolicitacaoReservaSala.STATUS_DEFERIDA,
            sala=self.sala_agendavel_b,
            data_inicio=data + timedelta(1),
            data_fim=data + timedelta(1),
            hora_inicio=time(8),
            hora_fim=time(10),
        )
        self.reserva_solicitacao_b = self.solicitacao_deferida_b.reservasala_set.latest('id')

    @prevent_logging_errors()
    def test_cancelar_reserva(self):
        """
        1. Só o perfil de Servidor avaliador de sala pode cancelar reserva
        2. O usuário corrente só pode cancelar reserva de sala que ele é avaliador
        3. UC 05 - Pós-condição: É enviado um e-mail para o solicitante da reserva que originou a reserva.
        """
        url_base = '/comum/sala/ver_solicitacao/{:d}/'
        url = '/comum/sala/cancelar_reserva/{:d}/'
        dados = {'justificativa_cancelamento': 'teste'}
        # Pode cancelar a reserva da solicitação a
        self.verificar_perfil_contains(
            url_base.format(self.solicitacao_deferida_a.id),
            text='href="{}"'.format(url).format(self.reserva_solicitacao_a.id),
            perfis_corretos=[GRUPO_AVALIADOR_SALA],
            perfis_errados=[GRUPO_SERVIDOR],
            error_status_code=403,
        )
        self.verificar_perfil_remover(
            url,
            [self.reserva_solicitacao_a.id, self.reserva_solicitacao_a.id],
            data=dados,
            queryset=ReservaSala.objects.exclude(cancelada=True),
            perfis_corretos=[GRUPO_AVALIADOR_SALA],
            perfis_errados=[GRUPO_SERVIDOR],
            success_status_code=302,
        )
        self.reserva_solicitacao_a.save()
        # UC 05 - Pós-condição: É enviado um e-mail para o solicitante da reserva que originou a reserva.
        avaliador_email = self.servidor_a.email
        requisitante_email = self.servidor_b.email
        interessado_email = self.servidor_c.email
        self.verificar_envio_email([avaliador_email, requisitante_email, interessado_email], '[SUAP] Reservas de Salas: Reserva Cancelada')

        # Servidor B tem permissão de cancelar a reserva da sala_b que ele é avaliador
        self.client.logout()
        self.client.login(user=self.servidor_b.user)
        self.verificar_perfil_contains(
            url_base.format(self.solicitacao_deferida_b.id),
            text='href="{}"'.format(url).format(self.reserva_solicitacao_b.id),
            perfis_corretos=[GRUPO_AVALIADOR_SALA],
            perfis_errados=[GRUPO_SERVIDOR],
            error_status_code=403,
            user=self.servidor_b.user,
        )
        self.verificar_perfil_remover(
            url,
            [self.reserva_solicitacao_b.id, self.reserva_solicitacao_b.id],
            data=dados,
            queryset=ReservaSala.objects.exclude(cancelada=True),
            perfis_corretos=[GRUPO_AVALIADOR_SALA],
            perfis_errados=[GRUPO_SERVIDOR],
            success_status_code=302,
            user=self.servidor_b.user,
        )
        self.reserva_solicitacao_b.save()
        # UC 05 - Pós-condição: É enviado um e-mail para o solicitante da reserva que originou a reserva.
        requisitante_email = self.servidor_a.email
        avaliador_email = self.servidor_b.email
        # não tem interessado
        self.verificar_envio_email([requisitante_email, avaliador_email], '[SUAP] Reservas de Salas: Reserva Cancelada')
        # Pode cancelar pois é o solicitante
        self.verificar_perfil_contains(
            url_base.format(self.solicitacao_deferida_a.id),
            text='href="{}"'.format(url).format(self.reserva_solicitacao_a.id),
            perfis_corretos=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR],
            user=self.servidor_b.user,
        )
        self.verificar_perfil_remover(
            url,
            [self.reserva_solicitacao_a.id, self.reserva_solicitacao_a.id],
            data=dados,
            queryset=ReservaSala.objects.exclude(cancelada=True),
            perfis_corretos=[GRUPO_SERVIDOR],
            success_status_code=302,
            user=self.servidor_b.user,
        )
        self.reserva_solicitacao_a.save()
        # UC 05 - Pós-condição: É enviado um e-mail para o solicitante da reserva que originou a reserva.
        avaliador_email = self.servidor_a.email
        requisitante_email = self.servidor_b.email
        interessado_email = self.servidor_c.email
        self.verificar_envio_email([avaliador_email, requisitante_email, interessado_email], '[SUAP] Reservas de Salas: Reserva Cancelada')

        # Servidor C não tem permissão de apagar nenhuma reserva porque ele não é avalidor de sala
        self.client.logout()
        self.client.login(user=self.servidor_c.user)

        self.verificar_perfil_contains(
            url_base.format(self.solicitacao_deferida_a.id),
            text='href="{}"'.format(url).format(self.reserva_solicitacao_a.id),
            perfis_errados=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR],
            error_status_code=403,
            user=self.servidor_c.user,
        )
        self.verificar_perfil_remover(
            url,
            [self.reserva_solicitacao_a.id, self.reserva_solicitacao_a.id],
            data=dados,
            queryset=ReservaSala.objects.exclude(cancelada=True),
            perfis_errados=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR],
            user=self.servidor_c.user,
        )

        self.verificar_perfil_contains(
            url_base.format(self.solicitacao_deferida_b.id),
            text='href="{}"'.format(url).format(self.reserva_solicitacao_b.id),
            perfis_errados=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR],
            error_status_code=403,
            user=self.servidor_c.user,
        )
        self.verificar_perfil_remover(
            url,
            [self.reserva_solicitacao_b.id, self.reserva_solicitacao_b.id],
            data=dados,
            queryset=ReservaSala.objects.exclude(cancelada=True),
            perfis_errados=[GRUPO_AVALIADOR_SALA, GRUPO_SERVIDOR],
            user=self.servidor_c.user,
        )


class IndeferirSolicitacaoForaPrazoTestCase(AgendamentoSalaBaseTestCase):
    def setUp(self):
        super().setUp()
        # Criando a base para teste
        SolicitacaoReservaSala.objects.all().delete()
        data = datetime.now().date()
        # solicitações não avaliadas
        self.solicitacao_antes_a = self.criar_solicitacao(
            solicitante=self.servidor_b.user, data_inicio=data + timedelta(-1), data_fim=data + timedelta(-1), hora_inicio=time(0), hora_fim=time(23)
        )
        self.solicitacao_atual_a = self.criar_solicitacao(solicitante=self.servidor_b.user, data_inicio=data, data_fim=data, hora_inicio=time(0), hora_fim=time(23))
        self.solicitacao_futura_a = self.criar_solicitacao(
            solicitante=self.servidor_b.user, data_inicio=data + timedelta(1), data_fim=data + timedelta(1), hora_inicio=time(0), hora_fim=time(23)
        )
        self.solicitacao_antes_b = self.criar_solicitacao(
            sala=self.sala_agendavel_b, data_inicio=data + timedelta(-1), data_fim=data + timedelta(-1), hora_inicio=time(0), hora_fim=time(23)
        )
        self.solicitacao_atual_b = self.criar_solicitacao(sala=self.sala_agendavel_b, data_inicio=data, data_fim=data, hora_inicio=time(0), hora_fim=time(23))
        self.solicitacao_futura_b = self.criar_solicitacao(
            sala=self.sala_agendavel_b, data_inicio=data + timedelta(1), data_fim=data + timedelta(1), hora_inicio=time(0), hora_fim=time(23)
        )

        # Solicitações deferidas
        self.solicitacao_deferida_antes_a = self.criar_solicitacao(
            status=SolicitacaoReservaSala.STATUS_DEFERIDA,
            solicitante=self.servidor_b.user,
            data_inicio=data + timedelta(-1),
            data_fim=data + timedelta(-1),
            hora_inicio=time(0),
            hora_fim=time(23),
        )
        self.solicitacao_deferida_atual_a = self.criar_solicitacao(
            status=SolicitacaoReservaSala.STATUS_DEFERIDA, solicitante=self.servidor_b.user, data_inicio=data, data_fim=data, hora_inicio=time(0), hora_fim=time(23)
        )
        self.solicitacao_deferida_futura_a = self.criar_solicitacao(
            status=SolicitacaoReservaSala.STATUS_DEFERIDA,
            solicitante=self.servidor_b.user,
            data_inicio=data + timedelta(1),
            data_fim=data + timedelta(1),
            hora_inicio=time(0),
            hora_fim=time(23),
        )
        self.solicitacao_deferida_antes_b = self.criar_solicitacao(
            status=SolicitacaoReservaSala.STATUS_DEFERIDA,
            sala=self.sala_agendavel_b,
            data_inicio=data + timedelta(-1),
            data_fim=data + timedelta(-1),
            hora_inicio=time(0),
            hora_fim=time(23),
        )
        self.solicitacao_deferida_atual_b = self.criar_solicitacao(
            status=SolicitacaoReservaSala.STATUS_DEFERIDA, sala=self.sala_agendavel_b, data_inicio=data, data_fim=data, hora_inicio=time(0), hora_fim=time(23)
        )
        self.solicitacao_deferida_futura_b = self.criar_solicitacao(
            status=SolicitacaoReservaSala.STATUS_DEFERIDA,
            sala=self.sala_agendavel_b,
            data_inicio=data + timedelta(1),
            data_fim=data + timedelta(1),
            hora_inicio=time(0),
            hora_fim=time(23),
        )

        # solicitações indeferidas
        self.solicitacao_indeferida_antes_a = self.criar_solicitacao(
            status=SolicitacaoReservaSala.STATUS_INDEFERIDA,
            solicitante=self.servidor_b.user,
            data_inicio=data + timedelta(-1),
            data_fim=data + timedelta(-1),
            hora_inicio=time(0),
            hora_fim=time(23),
        )
        self.solicitacao_indeferida_atual_a = self.criar_solicitacao(
            status=SolicitacaoReservaSala.STATUS_INDEFERIDA, solicitante=self.servidor_b.user, data_inicio=data, data_fim=data, hora_inicio=time(0), hora_fim=time(23)
        )
        self.solicitacao_indeferida_futura_a = self.criar_solicitacao(
            status=SolicitacaoReservaSala.STATUS_INDEFERIDA,
            solicitante=self.servidor_b.user,
            data_inicio=data + timedelta(1),
            data_fim=data + timedelta(1),
            hora_inicio=time(0),
            hora_fim=time(23),
        )
        self.solicitacao_indeferida_antes_b = self.criar_solicitacao(
            status=SolicitacaoReservaSala.STATUS_INDEFERIDA, sala=self.sala_agendavel_b, data_inicio=data + timedelta(-1), data_fim=data, hora_inicio=time(0), hora_fim=time(23)
        )
        self.solicitacao_indeferida_atual_b = self.criar_solicitacao(
            status=SolicitacaoReservaSala.STATUS_INDEFERIDA, sala=self.sala_agendavel_b, data_inicio=data, data_fim=data, hora_inicio=time(0), hora_fim=time(23)
        )
        self.solicitacao_indeferida_futura_b = self.criar_solicitacao(
            status=SolicitacaoReservaSala.STATUS_INDEFERIDA,
            sala=self.sala_agendavel_b,
            data_inicio=data + timedelta(1),
            data_fim=data + timedelta(1),
            hora_inicio=time(0),
            hora_fim=time(23),
        )

        # Recorrência
        hoje = datetime.now().date()
        # Pegando a segunda feira
        data = hoje + timedelta(-hoje.weekday())
        # data.weekday() = Monday is 0 and Sunday is 6
        # se for segunda terça ou quarta coloca a recorrencia sexta
        if hoje.weekday() in [0, 1, 2]:
            recorrencia = dict(recorrencia_sexta=True)
        else:
            recorrencia = dict(recorrencia_terca=True)

        data_inicio = data + timedelta(-7)
        data_fim = hoje + timedelta(1)
        # solicitação com data posterior mas que a data gerada não é posterior a data de hoje, ou seja, vai ser "atingida" pela indeferização
        self.solicitacao_semanal_antes = self.criar_solicitacao(
            data_inicio=data_inicio, data_fim=data_fim, hora_inicio=time(0), hora_fim=time(23), recorrencia=SolicitacaoReservaSala.RECORRENCIA_SEMANALMENTE, **recorrencia
        )

        # solicitação com data e data gerada posterior a data de hoje, ou seja, não vai ser "atingida" pela indeferização
        self.solicitacao_semanal_futura = self.criar_solicitacao(
            data_inicio=data_inicio,
            data_fim=data_fim + timedelta(7),
            hora_inicio=time(0),
            hora_fim=time(23),
            recorrencia=SolicitacaoReservaSala.RECORRENCIA_SEMANALMENTE,
            **recorrencia
        )

    def _test_indeferir_solicitacoes(self):
        # importlib.reload não funciona no python 3
        """
        1. Todas as solicitações de reservas não avaliadas fora de prazo, isto é,
        data final maior que data atual, serão automaticamente indeferidas.
        """

        def reload(obj):
            return obj.__class__.objects.get(id=obj.id)

        data_avaliacao = datetime.now()
        call_command('indeferir_solicitacoes_reserva_sala', verbosity=0)
        qtd_solicitacoes_avaliadas = SolicitacaoReservaSala.objects.filter(data_avaliacao__gte=data_avaliacao).count()
        self.assertEqual(qtd_solicitacoes_avaliadas, 3)

        # As solicitações que não foram avaliadas
        self.assertEqual(importlib.reload(self.solicitacao_antes_a).status, SolicitacaoReservaSala.STATUS_INDEFERIDA)
        self.assertEqual(importlib.reload(self.solicitacao_antes_b).status, SolicitacaoReservaSala.STATUS_INDEFERIDA)
        self.assertEqual(importlib.reload(self.solicitacao_atual_a).status, SolicitacaoReservaSala.STATUS_AGUARDANDO_AVALIACAO)
        self.assertEqual(importlib.reload(self.solicitacao_atual_b).status, SolicitacaoReservaSala.STATUS_AGUARDANDO_AVALIACAO)
        self.assertEqual(importlib.reload(self.solicitacao_futura_a).status, SolicitacaoReservaSala.STATUS_AGUARDANDO_AVALIACAO)
        self.assertEqual(importlib.reload(self.solicitacao_futura_b).status, SolicitacaoReservaSala.STATUS_AGUARDANDO_AVALIACAO)

        self.assertEqual(importlib.reload(self.solicitacao_semanal_antes).status, SolicitacaoReservaSala.STATUS_INDEFERIDA)
        self.assertEqual(importlib.reload(self.solicitacao_semanal_futura).status, SolicitacaoReservaSala.STATUS_AGUARDANDO_AVALIACAO)

        # Solicitações indeferidas continuam indeferidas
        self.assertEqual(importlib.reload(self.solicitacao_indeferida_antes_a).status, SolicitacaoReservaSala.STATUS_INDEFERIDA)
        self.assertEqual(importlib.reload(self.solicitacao_indeferida_antes_b).status, SolicitacaoReservaSala.STATUS_INDEFERIDA)
        self.assertEqual(importlib.reload(self.solicitacao_indeferida_atual_a).status, SolicitacaoReservaSala.STATUS_INDEFERIDA)
        self.assertEqual(importlib.reload(self.solicitacao_indeferida_atual_b).status, SolicitacaoReservaSala.STATUS_INDEFERIDA)

        # UC 04 - Primeira pós-condição: É enviado um e-mail para os solicitantes de reserva informando que a reserva foi avaliada;
        requisitante_email = self.servidor_b.email
        self.verificar_envio_email([requisitante_email], '[SUAP] Reservas de Salas: Solicitação Indeferida', qtd=3)
