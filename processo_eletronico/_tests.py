# -*- coding: utf-8 -*-
from datetime import datetime

from django.db import transaction

from comum.tests import SuapTestCase
from documento_eletronico.models import Classificacao
from processo_eletronico.models import Processo, TipoProcesso, Apensamento
from rh.models import Servidor

GRUPO_GERENTE_SISTEMICO = 'Gerente de processo eletronico sistêmico'
GRUPO_SERVIDOR = 'Servidor'

VISUALIZAR_COMO_PUBLICO = Processo.NIVEL_ACESSO_PUBLICO
VISUALIZAR_COMO_RESTRITO = Processo.NIVEL_ACESSO_RESTRITO
VISUALIZAR_COMO_PRIVADO = Processo.NIVEL_ACESSO_PRIVADO


class ProcessoEletronicoTestCase(SuapTestCase):
    def setUp(self):
        super(ProcessoEletronicoTestCase, self).setUp()

        self.client.login(user=self.servidor_a.user)

        # Classificação
        self.classificacao_1 = Classificacao.objects.create(codigo='código 1', descricao='descrição 1')
        self.classificacao_2 = Classificacao.objects.create(codigo='código 2', descricao='descrição 2')

        # Servidor no mesmo sertor do servidor_a
        self.servidor_a2 = Servidor.objects.create(
            nome='Servidor A2',
            matricula='a2',
            template='1',
            excluido=False,
            situacao=SuapTestCase.dict_initial_data['situacao_ativo_permanente'],
            cargo_emprego=SuapTestCase.dict_initial_data['cargo_emprego_a'],
            setor=SuapTestCase.dict_initial_data['setor_a1_suap'],
            setor_lotacao=SuapTestCase.dict_initial_data['setor_a1_siape'],
            setor_exercicio=SuapTestCase.dict_initial_data['setor_a1_siape'],
            email='servidor.a2@mail.gov',
            jornada_trabalho=SuapTestCase.dict_initial_data['jornada_trabalho'],
        )
        self.servidor_a2.user.set_password('123')
        self.servidor_a2.user.save()

    def verificar_perfil_submit_inserir(
        self,
        url,
        data={},
        queryset=None,
        verificar_sem_perfil=True,
        pode_sem_perfil=False,
        perfis_corretos=[],
        perfis_errados=[],
        incremento=1,
        success_status_code=200,
        error_status_code=403,
        after_submit=None,
        modificou=None,
        contains_text='Cadastro realizado com sucesso.',
        not_contains_text=None,
        user=None,
        contains_text_perfis_errados=None,
    ):
        self.verificar_perfil_submit(
            url,
            data,
            queryset,
            verificar_sem_perfil,
            pode_sem_perfil,
            perfis_corretos,
            perfis_errados,
            incremento,
            success_status_code,
            error_status_code,
            after_submit,
            modificou,
            contains_text,
            not_contains_text,
            user,
            contains_text_perfis_errados,
        )

    def verificar_perfil_submit_atualizar(
        self,
        url,
        data={},
        queryset=None,
        verificar_sem_perfil=True,
        pode_sem_perfil=False,
        perfis_corretos=[],
        perfis_errados=[],
        incremento=0,
        success_status_code=200,
        error_status_code=403,
        after_submit=None,
        modificou=None,
        contains_text='Atualização realizada com sucesso.',
        not_contains_text=None,
        user=None,
        contains_text_perfis_errados=None,
    ):
        self.verificar_perfil_submit(
            url,
            data,
            queryset,
            verificar_sem_perfil,
            pode_sem_perfil,
            perfis_corretos,
            perfis_errados,
            incremento,
            success_status_code,
            error_status_code,
            after_submit,
            modificou,
            contains_text,
            not_contains_text,
            user,
            contains_text_perfis_errados,
        )

    def verificar_perfil_submit_remover(
        self,
        url,
        data={},
        queryset=None,
        verificar_sem_perfil=True,
        pode_sem_perfil=False,
        perfis_corretos=[],
        perfis_errados=[],
        incremento=-1,
        success_status_code=200,
        error_status_code=403,
        after_submit=None,
        modificou=None,
        contains_text=': excluído com sucesso.',
        not_contains_text=None,
        user=None,
        contains_text_perfis_errados=None,
    ):
        self.verificar_perfil_submit(
            url,
            data,
            queryset,
            verificar_sem_perfil,
            pode_sem_perfil,
            perfis_corretos,
            perfis_errados,
            incremento,
            success_status_code,
            error_status_code,
            after_submit,
            modificou,
            contains_text,
            not_contains_text,
            user,
            contains_text_perfis_errados,
        )

    def __verificar_usuario(self, funcao, parametros, usuarios_corretos, usuarios_errados):
        """
        Executa a função para cada usuario em usuarios_corretos e usuarios_errados.

        Todos os dados são desfeitos, é dado ROLLBACK.

        :param funcao: função que executa a ação a ser testada
        :param parametros: parâmetros da função
        :param usuarios_corretos: usuário que podem executar a ação
        :param usuarios_errados: usuário que podem executar a ação
        :raise: AssertionError caso um usuário que não possa execute uma ação
        :return: Nada
        """

        def executar_funcao_e_desfazer(funcao, parametros):
            sid = transaction.savepoint()
            try:
                funcao(*parametros)
            finally:
                transaction.savepoint_rollback(sid)

        usuario_corrente = self.client.user
        for usuario in usuarios_corretos:
            self.client.logout()
            self.client.login(user=usuario)
            executar_funcao_e_desfazer(funcao, parametros)

        for usuario in usuarios_errados:
            self.client.logout()
            self.client.login(user=usuario)
            try:
                with self.assertRaises(AssertionError):
                    executar_funcao_e_desfazer(funcao, parametros)

            except AssertionError:
                raise AssertionError('Usuario "%s" conseguiu fazer a operação' % usuario)

        self.client.logout()
        self.client.login(user=usuario_corrente)

    def __get_usuarios(self, visualizar_como):
        if visualizar_como == VISUALIZAR_COMO_PUBLICO:
            usuarios_corretos = [self.servidor_a.user, self.servidor_a2.user, self.servidor_b.user]
            usuarios_errados = []
        elif visualizar_como == VISUALIZAR_COMO_RESTRITO:
            usuarios_corretos = [self.servidor_a.user, self.servidor_a2.user]
            usuarios_errados = [self.servidor_b.user]
        elif visualizar_como == VISUALIZAR_COMO_PRIVADO:
            usuarios_corretos = [self.servidor_a.user]
            usuarios_errados = [self.servidor_a2.user, self.servidor_b.user]

        return usuarios_corretos, usuarios_errados

    def __verificar_contains_processo(self, url, texto):
        self.verificar_perfil_contains(url, text=texto, perfis_corretos=[GRUPO_SERVIDOR], perfis_errados=[GRUPO_GERENTE_SISTEMICO], error_status_code=403)

    #################
    # TipoDocumento #
    #################
    def get_dados_tipo_processo(self, kwargs={}):
        initial_data = dict(nome='Tipo de Processo', nivel_acesso_default=Processo.NIVEL_ACESSO_PRIVADO)
        initial_data.update(kwargs)
        return initial_data

    def _cadastrar_tipo_processo(self, kwargs={}):
        """
        Somente o GRUPO_GERENTE_SISTEMICO pode cadastrar TipoProcesso
        """
        dados = self.get_dados_tipo_processo()
        self.verificar_perfil_contains(
            '/admin/processo_eletronico/tipoprocesso/',
            text='Adicionar Tipo de Processo',
            perfis_corretos=[GRUPO_GERENTE_SISTEMICO],
            perfis_errados=[GRUPO_SERVIDOR],
            error_status_code=403,
        )

        url = '/admin/processo_eletronico/tipoprocesso/add/'
        self.verificar_perfil_submit_inserir(url, dados, TipoProcesso.objects, perfis_corretos=[GRUPO_GERENTE_SISTEMICO], perfis_errados=[GRUPO_SERVIDOR])

    def _editar_tipo_processo(self, kwargs={}):
        """
        Somente o GRUPO_GERENTE_SISTEMICO pode editar TipoProcesso
        """
        dados = self.get_dados_tipo_processo(kwargs)
        tipo_processo = TipoProcesso.objects.last()
        url = '/admin/processo_eletronico/tipoprocesso/%d/change/' % tipo_processo.id
        self.verificar_perfil_contains(
            '/admin/processo_eletronico/tipoprocesso/', text=url, perfis_corretos=[GRUPO_GERENTE_SISTEMICO], perfis_errados=[GRUPO_SERVIDOR], error_status_code=403
        )

        self.assertNotEqual(tipo_processo.nome, dados['nome'])
        self.verificar_perfil_submit_atualizar(url, dados, TipoProcesso.objects, perfis_corretos=[GRUPO_GERENTE_SISTEMICO], perfis_errados=[GRUPO_SERVIDOR])

        tipo_processo.refresh_from_db()
        self.assertEqual(tipo_processo.nome, dados['nome'])

    def _listar_tipo_processo(self, content):
        """
        Somente o GRUPO_GERENTE_SISTEMICO pode listar TipoProcesso
        """
        self.verificar_perfil_contains(
            '/admin/processo_eletronico/tipoprocesso/', text=content, perfis_corretos=[GRUPO_GERENTE_SISTEMICO], perfis_errados=[GRUPO_SERVIDOR], error_status_code=403
        )

    def _remover_tipo_processo(self):
        """
        Somente o GRUPO_GERENTE_SISTEMICO pode remover TipoProcesso
        """
        tipo_processo = TipoProcesso.objects.last()
        url = '/admin/processo_eletronico/tipoprocesso/%d/change/' % tipo_processo.id
        self.verificar_perfil_not_contains(url, text='Apagar', perfis_corretos=[GRUPO_GERENTE_SISTEMICO])

        dados = dict(submit='Sim, tenho certeza')
        url = '/admin/processo_eletronico/tipoprocesso/%d/delete/' % tipo_processo.id
        self.verificar_perfil_submit_remover(url, dados, TipoProcesso.objects, perfis_errados=[GRUPO_GERENTE_SISTEMICO, GRUPO_SERVIDOR])

    ############
    # Processo #
    ############
    def get_dados_processo(self, kwargs={}):
        id_tipo = TipoProcesso.objects.last().id
        initial_data = dict(
            tipo_processo=id_tipo,
            nivel_acesso=Processo.NIVEL_ACESSO_PUBLICO,
            assunto='assunto %s' % datetime.now(),
            interessados=[self.servidor_d.id],
            classificacoes=[self.classificacao_1.id],
        )
        initial_data.update(kwargs)
        return initial_data

    def get_dados_atualizar_processo(self, processo, kwargs={}):
        initial_data = dict(
            tipo_processo=processo.tipo_processo_id, nivel_acesso=processo.nivel_acesso, assunto=processo.assunto, interessados=processo.interessados.values_list('id', flat=True)
        )
        initial_data.update(kwargs)
        return initial_data

    def _cadastrar_processo(self, kwargs={}):
        dados = self.get_dados_processo(kwargs)
        self.__verificar_contains_processo('/admin/processo_eletronico/processo/', 'Adicionar Processo')

        url = '/admin/processo_eletronico/processo/add/'
        self.verificar_perfil_submit_inserir(url, dados, Processo.objects, perfis_corretos=[GRUPO_SERVIDOR], perfis_errados=[GRUPO_GERENTE_SISTEMICO])

    def _visualizar_processo(self, processo, visualizar_como=None, usuarios_corretos=None, usuarios_errados=None):
        if visualizar_como:
            usuarios_corretos, usuarios_errados = self.__get_usuarios(visualizar_como)

        def __verificar_contains_processo(self, url, texto):
            self.verificar_perfil_contains(
                url, text=texto, pode_sem_perfil=True, perfis_corretos=[GRUPO_SERVIDOR, GRUPO_GERENTE_SISTEMICO], perfis_errados=[], error_status_code=403
            )

        self.__verificar_usuario(
            __verificar_contains_processo,
            (self, '/processo_eletronico/processo/%d/' % processo.id, processo.assunto),
            usuarios_corretos=usuarios_corretos,
            usuarios_errados=usuarios_errados,
        )

    def _test_editar_processo_pessoas(self, processo, url, dados, visualizar_como=None, usuarios_corretos=None, usuarios_errados=None):
        def __editar_processo(self, processo):
            processo.refresh_from_db()
            self.assertNotEqual(processo.assunto, dados['assunto'])
            self.verificar_perfil_submit_atualizar(
                url, dados, Processo.objects, contains_text='Atualização realizada com sucesso.', perfis_corretos=[GRUPO_SERVIDOR], perfis_errados=[GRUPO_GERENTE_SISTEMICO]
            )
            processo.refresh_from_db()
            self.assertEqual(processo.assunto, dados['assunto'])

        if visualizar_como:
            usuarios_corretos, usuarios_errados = self.__get_usuarios(visualizar_como)

        self.__verificar_usuario(__editar_processo, (self, processo), usuarios_corretos=usuarios_corretos, usuarios_errados=usuarios_errados)

    def _editar_processo(self, processo, visualizar_como=None, usuarios_corretos=None, usuarios_errados=None):
        assunto = 'assunto %s' % datetime.now()
        dados = self.get_dados_atualizar_processo(processo, dict(assunto=assunto))
        url = '/admin/processo_eletronico/processo/%d/change/' % processo.id
        self._test_editar_processo_pessoas(processo, url, dados, visualizar_como, usuarios_corretos, usuarios_errados)
        self.__verificar_contains_processo('/admin/processo_eletronico/processo/', url)
        processo.refresh_from_db()
        self.assertNotEqual(processo.assunto, assunto)
        self.verificar_perfil_submit_atualizar(
            url, dados, Processo.objects, contains_text='Atualização realizada com sucesso.', perfis_corretos=[GRUPO_SERVIDOR], perfis_errados=[GRUPO_GERENTE_SISTEMICO]
        )
        processo.refresh_from_db()
        self.assertEqual(processo.assunto, assunto)

    def _listar_processo(self, content, visualizar_como=None, usuarios_corretos=None, usuarios_errados=None):
        if visualizar_como:
            usuarios_corretos, usuarios_errados = self.__get_usuarios(visualizar_como)

        self.__verificar_usuario(
            self.__verificar_contains_processo, ('/admin/processo_eletronico/processo/', content), usuarios_corretos=usuarios_corretos, usuarios_errados=usuarios_errados
        )

    def _remover_processo(self, processo):
        def __remover_processo(self, documento):
            # Não pode remover documento
            documento = Processo.objects.last()
            url = '/admin/processo_eletronico/processo/%d/delete/' % documento.id
            self.verificar_perfil_status(url, perfis_errados=[GRUPO_GERENTE_SISTEMICO, GRUPO_SERVIDOR])

            dados = dict(submit='Sim, tenho certeza')
            self.verificar_perfil_submit_remover(url, dados, Processo.objects, perfis_errados=[GRUPO_GERENTE_SISTEMICO, GRUPO_SERVIDOR])

        usuarios_corretos, usuarios_errados = self.__get_usuarios(VISUALIZAR_COMO_PUBLICO)
        self.__verificar_usuario(__remover_processo, (self, processo), usuarios_corretos=usuarios_corretos, usuarios_errados=[])

    def __verificar_status_processo(self, url, success_status_code=200, error_status_code=403):
        self.verificar_perfil_status(
            url,
            pode_sem_perfil=True,
            perfis_corretos=[GRUPO_SERVIDOR, GRUPO_GERENTE_SISTEMICO],
            perfis_errados=[],
            success_status_code=success_status_code,
            error_status_code=error_status_code,
        )

    def _imprimir_processo(self, processo, visualizar_como=None, usuarios_corretos=None, usuarios_errados=None):
        if visualizar_como:
            usuarios_corretos, usuarios_errados = self.__get_usuarios(visualizar_como)

        self.__verificar_usuario(
            self.__verificar_status_processo, ('/processo_eletronico/imprimir_processo/%d/' % processo.id,), usuarios_corretos=usuarios_corretos, usuarios_errados=usuarios_errados
        )

        self.__verificar_status_processo('/processo_eletronico/imprimir_processo/%d/' % processo.id)

    def test_anexar_processo(self):
        # Portaria Interministerial 1.677 de 7 de outubro de 2015
        # 2.10.1.2  -  Juntada  por  anexação  de  processo(s)  a  processo
        #         Esta  juntada  se  caracteriza  pela  união  de  um  ou  mais  pro-
        # cessos  (processos  acessórios)  a  outro  processo  (processo  principal),
        # desde que referentes a um mesmo interessado e assunto, prevalecendo
        # o  número  do  processo  mais  antigo,  ou  seja,  o  processo  principal.
        self._cadastrar_tipo_processo()
        return
        assunto = 'assunto %s' % datetime.now()
        self._cadastrar_processo(dict(assunto=assunto))
        processo_antigo_1 = Processo.objects.get(assunto=assunto)

        assunto = 'assunto %s' % datetime.now()
        self._cadastrar_processo(dict(assunto=assunto))
        processo_novo_1 = Processo.objects.get(assunto=assunto)

        dados = dict(justificativa='Justificativa %s' % datetime.now(), processos_anexados=[processo_novo_1.id])
        url = '/processo_eletronico/anexar_processos/%s/' % processo_antigo_1.id
        self.verificar_perfil_submit_inserir(url, dados, processo_antigo_1.get_processos_anexados(), pode_sem_perfil=True, contains_text='Processo(s) anexado(s) com sucesso!')

        self.assertEqual(processo_novo_1.get_processos_anexados().count(), 0)

        # Não é permitido a visualização de processo anexado
        url = '/processo_eletronico/processo/%s/'
        response = self.client.get(url % processo_novo_1.id, follow=True)
        self.assertEqual(response.status_code, 403)

        # Deve permanecer o mais antigo
        assunto = 'assunto %s' % datetime.now()
        self._cadastrar_processo(dict(assunto=assunto))
        processo_antigo_2 = Processo.objects.get(assunto=assunto)

        assunto = 'assunto %s' % datetime.now()
        self._cadastrar_processo(dict(assunto=assunto))
        processo_novo_2 = Processo.objects.get(assunto=assunto)

        dados = dict(justificativa='Justificativa %s' % datetime.now(), processos_anexados=[processo_antigo_2.id])

        url = '/processo_eletronico/anexar_processos/%s/' % processo_novo_2.id
        # O mais novo fica anexado ao mais antigo
        self.verificar_perfil_submit_inserir(url, dados, processo_antigo_2.get_processos_anexados(), pode_sem_perfil=True, contains_text='Processo(s) anexado(s) com sucesso!')

        #  Não permitir anexação de processos com interessados diferentes
        assunto = 'assunto %s' % datetime.now()
        self._cadastrar_processo(dict(assunto=assunto, interessados=[self.servidor_a.id]))
        processo_antigo = Processo.objects.get(assunto=assunto)

        assunto = 'assunto %s' % datetime.now()
        self._cadastrar_processo(dict(assunto=assunto, interessados=[self.servidor_b.id]))
        processo_novo = Processo.objects.get(assunto=assunto)

        dados = dict(justificativa='Justificativa %s' % datetime.now(), processos_anexados=[processo_novo.id])

        url = '/processo_eletronico/anexar_processos/%s/' % processo_antigo.id
        self.verificar_perfil_submit_inserir(url, dados, processo_antigo.get_processos_anexados(), incremento=0, pode_sem_perfil=True)

        #  É permitir anexação de processos com assuntos diferentes
        # FIXME: o que seria assuntos? estamos tratando como classificação, será permitido mesmo?
        assunto = 'assunto %s' % datetime.now()
        self._cadastrar_processo(dict(assunto=assunto, classificacoes=[self.classificacao_1.id]))
        processo_antigo = Processo.objects.get(assunto=assunto)

        assunto = 'assunto %s' % datetime.now()
        self._cadastrar_processo(dict(assunto=assunto, classificacoes=[self.classificacao_2.id]))
        processo_novo = Processo.objects.get(assunto=assunto)

        dados = dict(justificativa='Justificativa %s' % datetime.now(), processos_anexados=[processo_novo.id])
        url = '/processo_eletronico/anexar_processos/%s/' % processo_antigo.id
        self.verificar_perfil_submit_inserir(url, dados, processo_antigo.get_processos_anexados(), pode_sem_perfil=True)

    def _apensar_processo(self, processo_apensador, processos_a_apensar):
        dados = dict(justificativa='Justificativa %s' % datetime.now(), processos_a_apensar=processos_a_apensar)
        # FIXME: Tive que fazer assim porque não consegui com o self.verificar_perfil_submit_inserir
        url = '/processo_eletronico/apensar_processos/%s/' % processo_apensador.id
        response = self.client.post(url, dados, follow=True)
        self.assertContains(response, 'Processo(s) apensado(s) com sucesso!')
        return response

    def test_apensar_processo(self):
        # Portaria Interministerial 1.677 de 7 de outubro de 2015
        # 2.10.2  -  Juntada  por  apensação  de  processo(s)  a  processo
        #         A juntada por apensação de processo(s) a processo ocorre em
        # caráter  temporário  e  tem  como  objetivo  o  estudo,  a  instrução  e  a
        # uniformidade  de  tratamento  em  matérias  semelhantes,  pertencentes  a
        # um  mesmo  interessado  ou  não.  Cada  processo  conserva  sua  iden-
        # tidade  e  independência.
        #         Esta  juntada  se  caracteriza  pela  junção  de  um  ou  mais  pro-
        # cessos  (processos  acessórios)  a  outro  processo  (processo  principal).
        # Neste procedimento, considera-se como processo principal o que con-
        # tiver  o  pedido  da  juntada  por  apensação,  observando-se  que  este  não
        # será,  necessariamente,  o  processo  mais  antigo.
        #         Sempre  que  ocorre  uma  juntada  por  apensação,  os  processos
        # passam a tramitar juntos e o acréscimo de novas folhas deverá ocorrer
        # somente  no  processo  principal.
        #         Nos  processos  digitais,  é  possível  associar  ou  vincular  dois
        # ou  mais  processos  com  matérias  semelhantes  de  maneira  que  o  trâ-
        # mite  de  cada  um  siga  independentemente  e  o  acréscimo  de  novos
        # documentos  possa  ser  realizado  em  todos  eles.  No  entanto,  este  pro-
        # cedimento  não  se  caracteriza  por  juntada.  Quando  se  optar  pela  rea-
        # lização  de  uma  juntada  por  apensação,  os  processos  necessariamente
        # passarão  a  tramitar  juntos.
        # FIXME: o que seria materias semelhantes?

        self._cadastrar_tipo_processo()

        assunto = 'assunto %s' % datetime.now()
        self._cadastrar_processo(dict(assunto=assunto))
        processo_apensador = Processo.objects.get(assunto=assunto)

        assunto = 'assunto %s' % datetime.now()
        self._cadastrar_processo(dict(assunto=assunto))
        processo_apensado = Processo.objects.get(assunto=assunto)

        self._apensar_processo(processo_apensador, [processo_apensado.id])
        # dados = dict(
        #     justificativa       = 'Justificativa %s' % datetime.now(),
        #     processos_a_apensar = [processo_apensado.id]
        # )
        # # FIXME: Tive que fazer assim porque não consegui com o self.verificar_perfil_submit_inserir
        # url = '/processo_eletronico/apensar_processos/%s/' % processo_apensador.id
        # response = self.client.post(url, dados, follow=True)
        # self.assertContains(response, u'Processo(s) apensado(s) com sucesso!')
        self.assertEqual(processo_apensador.get_processos_apensados().count(), 1)
        self.assertEqual(processo_apensado.get_processos_apensados().count(), 1)

    def _desapensar_processo(self, processo):
        dados = dict(justificativa='Justificativa %s' % datetime.now())
        # FIXME: Tive que fazer assim porque não consegui com o self.verificar_perfil_submit_inserir
        url = '/processo_eletronico/desapensar_processo/%s/' % processo.id
        self.client.post(url, dados, follow=True)

    def test_desapensar_processo(self):
        """
        Testa o desapensamento de um processo quando tem mais de dois processos apensados.
        """
        self._cadastrar_tipo_processo()

        assunto = 'assunto %s' % datetime.now()
        self._cadastrar_processo(dict(assunto=assunto))
        processo_apensador = Processo.objects.get(assunto=assunto)

        assunto = 'assunto %s' % datetime.now()
        self._cadastrar_processo(dict(assunto=assunto))
        processo_apensado1 = Processo.objects.get(assunto=assunto)

        assunto = 'assunto %s' % datetime.now()
        self._cadastrar_processo(dict(assunto=assunto))
        processo_apensado2 = Processo.objects.get(assunto=assunto)

        self._apensar_processo(processo_apensador, [processo_apensado1.id, processo_apensado2.id])

        apensamento = Apensamento.objects.get(apensamentoprocesso__processo=processo_apensador)
        self.assertIsNone(apensamento.data_hora_remocao)
        apensamentos_processos = apensamento.apensamentoprocesso_set.all()
        for apensamento_processo in apensamentos_processos:
            self.assertIsNone(apensamento_processo.data_hora_remocao)

        self._desapensar_processo(processo_apensado2)
        apensamento.refresh_from_db()
        self.assertIsNone(apensamento.data_hora_remocao)
        apensamentos_processos = apensamento.apensamentoprocesso_set.all()
        for apensamento_processo in apensamentos_processos:
            if apensamento_processo.processo == processo_apensado2:
                self.assertIsNotNone(apensamento_processo.data_hora_remocao)
            else:
                self.assertIsNone(apensamento_processo.data_hora_remocao)

    def test_desapensar_processos_finalizar_apensamento(self):
        """
        Testa o desapensamento de um processo quando só tem dois processos apensados.
        Neste caso ao desapensar um processo o apensamento todo é finalizado, já que só iria ficar um processo.
        """
        self._cadastrar_tipo_processo()

        assunto = 'assunto %s' % datetime.now()
        self._cadastrar_processo(dict(assunto=assunto))
        processo_apensador = Processo.objects.get(assunto=assunto)

        assunto = 'assunto %s' % datetime.now()
        self._cadastrar_processo(dict(assunto=assunto))
        processo_apensado = Processo.objects.get(assunto=assunto)

        self._apensar_processo(processo_apensador, [processo_apensado.id])

        apensamento = Apensamento.objects.get(apensamentoprocesso__processo=processo_apensador)
        self.assertIsNone(apensamento.data_hora_remocao)
        apensamentos_processos = apensamento.apensamentoprocesso_set.all()
        for apensamento_processo in apensamentos_processos:
            self.assertIsNone(apensamento_processo.data_hora_remocao)

        self._desapensar_processo(processo_apensado)
        apensamento.refresh_from_db()
        self.assertIsNotNone(apensamento.data_hora_remocao)
        apensamentos_processos = apensamento.apensamentoprocesso_set.all()
        for apensamento_processo in apensamentos_processos:
            self.assertIsNotNone(apensamento_processo.data_hora_remocao)

    ###################
    # FLUXO PRINCIPAL #
    ###################
    def test_fluxo(self):
        ####################
        # Tipo de Processo #
        ####################
        self._cadastrar_tipo_processo()
        nome_tipo = 'tipo_processo%s' % datetime.now()
        self._editar_tipo_processo(dict(nome=nome_tipo))
        self._listar_tipo_processo(nome_tipo)
        self._remover_tipo_processo()

        ############
        # Processo #
        ############
        self._cadastrar_processo()
        processo = Processo.objects.last()
        # FIXME: qualquer processo público pode ser acessado por qualquer um a qualquer momento? ou só quando ocorrer o primeiro trâmite?
        self._visualizar_processo(processo, VISUALIZAR_COMO_PUBLICO)
        self._editar_processo(processo, VISUALIZAR_COMO_RESTRITO)
        processo.refresh_from_db()
        self._listar_processo(processo.assunto, VISUALIZAR_COMO_PUBLICO)
        self._remover_processo(processo)
        self._imprimir_processo(processo, VISUALIZAR_COMO_PUBLICO)
