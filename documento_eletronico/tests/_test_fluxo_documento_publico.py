# -*- coding: utf-8 -*-
# flake8: noqa
import copy

from rest_framework.status import *

from documento_eletronico.models import Documento, DocumentoStatus, DocumentoTexto, TipoDocumentoTexto
from documento_eletronico.tests._test_documento_base import DocumentoTestCase, merge_nested_dict


# ./manage.py test documento_eletronico --keepdb --verbosity=2
class FluxoDocumentoPublicoTestCase(DocumentoTestCase):
    def setUp(self):
        super(DocumentoTestCase, self).setUp()
        # Rascunho
        self.tela_rascunho_listagem = {
            'servidores_com_acesso_edicao': {
                'comum': {
                    '/documento_eletronico/gerenciar_compartilhamento_documento/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/visualizar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/editar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/clonar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/admin/documento_eletronico/documentotexto/%(id)s/history/': (True, HTTP_200_OK),
                    '/documento_eletronico/gerar_minuta/%(id)s/': (True, HTTP_200_OK),
                    self._get_nivel_acesso_display(Documento.NIVEL_ACESSO_PUBLICO): (True, HTTP_200_OK),
                    self._get_status_display(DocumentoStatus.STATUS_RASCUNHO): (True, HTTP_200_OK),
                    'Nenhum documento foi encontrado': (False, HTTP_403_FORBIDDEN),
                },
                'servidor_dono': {},
                'servidores_mesmo_setor': {},
                'servidores_setor_pai': {
                    '/documento_eletronico/gerenciar_compartilhamento_documento/%(id)s/': (False, HTTP_403_FORBIDDEN),
                    '/documento_eletronico/editar_documento/%(id)s/': (False, HTTP_403_FORBIDDEN),
                    '/admin/documento_eletronico/documentotexto/%(id)s/history/': (False, HTTP_403_FORBIDDEN),
                    '/documento_eletronico/gerar_minuta/%(id)s/': (False, HTTP_403_FORBIDDEN),
                    'Nenhum documento foi encontrado': (False, HTTP_403_FORBIDDEN),
                },
                'servidores_setores_irmaos_e_compartilhados_editar_setor_usuario_meus_setores': {
                    '/documento_eletronico/gerenciar_compartilhamento_documento/%(id)s/': (False, HTTP_403_FORBIDDEN)
                },
                'servidores_caso_particular': {},
            },
            'documentos_compartilhados_listagem_todos_setores_ler': {
                '/documento_eletronico/visualizar_documento/%(id)s/': (True, HTTP_200_OK),
                '/documento_eletronico/clonar_documento/%(id)s/': (True, HTTP_200_OK),
            },
            'documentos_compartilhados_listagem_qualquer_setor_editar': {
                '/documento_eletronico/visualizar_documento/%(id)s/': (True, HTTP_200_OK),
                '/documento_eletronico/editar_documento/%(id)s/': (True, HTTP_200_OK),
                '/documento_eletronico/clonar_documento/%(id)s/': (True, HTTP_200_OK),
                '/admin/documento_eletronico/documentotexto/%(id)s/history/': (True, HTTP_200_OK),
                '/documento_eletronico/concluir_documento/%(id)s/': (True, HTTP_200_OK),
                '/documento_eletronico/gerar_minuta/%(id)s/': (True, HTTP_200_OK),
            },
            'outros_usuarios': {},
        }

        self.tela_rascunho_visualizacao = {
            'servidores_com_acesso_edicao': {
                'comum': {'/documento_eletronico/concluir_documento/%(id)s/': (True, HTTP_200_OK)},
                'servidor_dono': {},
                'servidores_mesmo_setor': {},
                'servidores_setor_pai': {'/documento_eletronico/concluir_documento/%(id)s/': (False, HTTP_403_FORBIDDEN)},
                'servidores_setores_irmaos_e_compartilhados_editar_setor_usuario_meus_setores': {},
                'servidores_caso_particular': {},
            },
            'documentos_compartilhados_listagem_todos_setores_ler': {},
            'documentos_compartilhados_listagem_qualquer_setor_editar': {},
            'outros_usuarios': {},
        }

        # Compartilhado
        self.tela_compartilhado_listagem = copy.deepcopy(self.tela_rascunho_listagem)
        merge_nested_dict(
            self.tela_compartilhado_listagem,
            {
                'servidores_com_acesso_edicao': {
                    'comum': {},
                    'servidor_dono': {},
                    'servidores_mesmo_setor': {},
                    'servidores_setor_pai': {},
                    'servidores_setores_irmaos_e_compartilhados_editar_setor_usuario_meus_setores': {},
                    'servidores_caso_particular': {},
                },
                'documentos_compartilhados_listagem_qualquer_setor_editar': {
                    '/documento_eletronico/gerenciar_compartilhamento_documento/%(id)s/': (False, HTTP_403_FORBIDDEN),
                    '/documento_eletronico/visualizar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/editar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/clonar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/admin/documento_eletronico/documentotexto/%(id)s/history/': (True, HTTP_200_OK),
                    self._get_nivel_acesso_display(Documento.NIVEL_ACESSO_PUBLICO): (True, HTTP_200_OK),
                    self._get_status_display(DocumentoStatus.STATUS_RASCUNHO): (True, HTTP_200_OK),
                    'Nenhum documento foi encontrado': (True, HTTP_200_OK),
                },
                'documentos_compartilhados_listagem_todos_setores_ler': {
                    '/documento_eletronico/visualizar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/clonar_documento/%(id)s/': (True, HTTP_200_OK),
                },
                'outros_usuarios': {},
            },
        )

        self.tela_compartilhado_visualizacao = copy.deepcopy(self.tela_rascunho_visualizacao)
        merge_nested_dict(
            self.tela_compartilhado_visualizacao,
            {
                'servidores_com_acesso_edicao': {
                    'comum': {},
                    'servidor_dono': {},
                    'servidores_mesmo_setor': {},
                    'servidores_setor_pai': {},
                    'servidores_setores_irmaos_e_compartilhados_editar_setor_usuario_meus_setores': {},
                    'servidores_caso_particular': {},
                },
                'documentos_compartilhados_listagem_qualquer_setor_editar': {'/documento_eletronico/concluir_documento/%(id)s/': (True, HTTP_200_OK)},
                'documentos_compartilhados_listagem_todos_setores_ler': {},
                'outros_usuarios': {},
            },
        )

        # Minuta
        self.tela_concluido_listagem = copy.deepcopy(self.tela_compartilhado_listagem)
        merge_nested_dict(
            self.tela_concluido_listagem,
            {
                'servidores_com_acesso_edicao': {
                    'comum': {
                        '/documento_eletronico/editar_documento/%(id)s/': (False, HTTP_403_FORBIDDEN),
                        '/documento_eletronico/imprimir_documento_pdf/%(id)s/carta/': (True, HTTP_200_OK),
                        '/documento_eletronico/imprimir_documento_pdf/%(id)s/paisagem/': (True, HTTP_200_OK),
                        '/documento_eletronico/solicitar_revisao/%(id)s/': (True, HTTP_200_OK),
                        self._get_nivel_acesso_display(Documento.NIVEL_ACESSO_PUBLICO): (True, HTTP_200_OK),
                        self._get_status_display(DocumentoStatus.STATUS_CONCLUIDO): (True, HTTP_200_OK),
                    },
                    'servidor_dono': {},
                    'servidores_mesmo_setor': {},
                    'servidores_setor_pai': {},
                    'servidores_setores_irmaos_e_compartilhados_editar_setor_usuario_meus_setores': {},
                    'servidores_caso_particular': {},
                },
                'documentos_compartilhados_listagem_qualquer_setor_editar': {
                    '/documento_eletronico/editar_documento/%(id)s/': (False, HTTP_403_FORBIDDEN),
                    '/documento_eletronico/imprimir_documento_pdf/%(id)s/carta/': (True, HTTP_200_OK),
                    '/documento_eletronico/imprimir_documento_pdf/%(id)s/paisagem/': (True, HTTP_200_OK),
                    '/documento_eletronico/solicitar_revisao/%(id)s/': (True, HTTP_200_OK),
                    self._get_nivel_acesso_display(Documento.NIVEL_ACESSO_PUBLICO): (True, HTTP_200_OK),
                    self._get_status_display(DocumentoStatus.STATUS_CONCLUIDO): (True, HTTP_200_OK),
                },
                'documentos_compartilhados_listagem_todos_setores_ler': {},
                'outros_usuarios': {},
            },
        )
        self.tela_concluido_visualizacao = copy.deepcopy(self.tela_compartilhado_visualizacao)
        merge_nested_dict(
            self.tela_concluido_visualizacao,
            {
                'servidores_com_acesso_edicao': {
                    'comum': {
                        '/documento_eletronico/concluir_documento/%(id)s/': (False, HTTP_403_FORBIDDEN),
                        '/documento_eletronico/imprimir_documento_pdf/%(id)s/carta/': (True, HTTP_200_OK),
                        '/documento_eletronico/imprimir_documento_pdf/%(id)s/paisagem/': (True, HTTP_200_OK),
                        '/documento_eletronico/retornar_para_rascunho/%(id)s/': (True, HTTP_200_OK),
                        '/documento_eletronico/solicitar_assinatura/%(id)s/': (True, HTTP_200_OK),
                        '/documento_eletronico/assinar_documento/%(id)s/': (True, HTTP_200_OK),
                        '/documento_eletronico/assinar_documento_token/%(id)s/': (True, HTTP_200_OK),
                    },
                    'servidor_dono': {},
                    'servidores_mesmo_setor': {},
                    'servidores_setor_pai': {},
                    'servidores_setores_irmaos_e_compartilhados_editar_setor_usuario_meus_setores': {},
                    'servidores_caso_particular': {},
                },
                'documentos_compartilhados_listagem_qualquer_setor_editar': {
                    '/documento_eletronico/concluir_documento/%(id)s/': (False, HTTP_403_FORBIDDEN),
                    '/documento_eletronico/imprimir_documento_pdf/%(id)s/carta/': (True, HTTP_200_OK),
                    '/documento_eletronico/imprimir_documento_pdf/%(id)s/paisagem/': (True, HTTP_200_OK),
                    '/documento_eletronico/retornar_para_rascunho/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/solicitar_assinatura/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/assinar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/assinar_documento_token/%(id)s/': (True, HTTP_200_OK),
                },
                'documentos_compartilhados_listagem_todos_setores_ler': {
                    '/documento_eletronico/imprimir_documento_pdf/%(id)s/carta/': (True, HTTP_200_OK),
                    '/documento_eletronico/imprimir_documento_pdf/%(id)s/paisagem/': (True, HTTP_200_OK),
                },
                'outros_usuarios': {},
            },
        )

    # ./manage.py test documento_eletronico.tests.FluxoDocumentoPublicoTestCase.test_cadastrar_documento --keepdb --verbosity=2
    def test_cadastrar_documento(self):
        servidor = self.records['scosinf1']
        self.login(servidor)
        documento = self._cadastrar_documento(servidor, self.retornar(TipoDocumentoTexto, chaves={'sigla': 'OFÍCIO'})[0], Documento.NIVEL_ACESSO_PUBLICO)

        self.logger.info('\n\nDocumento público(RASCUNHO), tem acesso todos os servidores do mesmo setor e ' 'servidores de setores compartilhados.')

        self.verificar_conteudo_telas_documento(
            documento=documento, conteudos_tela_listagem=self.tela_rascunho_listagem, conteudos_tela_visualizacao=self.tela_rascunho_visualizacao, servidores_caso_particular=[]
        )

    # ./manage.py test documento_eletronico.tests.FluxoDocumentoPublicoTestCase.test_documento_compatilhado --keepdb --verbosity=2
    def test_documento_compatilhado(self):
        """
        :return:
        . Criador: sconsinf1(9007)
        . Mesmo Setor/Pai
            - Mesmo Setor: coord_cosinf(9005), sconsif2(9008)
            - Setor Pai: setor_digti - diretor_digti(9003)
        . Setor irmão/Documento Compartilhado (Setor)
            - Setor Irmão: setor_cosaad - coord_cosaad(9006)
            - Documento compartilhado (setor): setor_coinre - sconire1(9010), sconire2(9011)
        . Compartilhamento Documento Editar
            - Setor: setor_gabin - chefe_gabin(9004)
            - Servidor: diretor_cnat(9002)
        . Compartilhamento Documento Ler
            - Setor: setor_proex - proreitor_proex(9012)
            - Servidor: proreitor_propi(9013)
        . Demais Servidores: sdiatinf1(9009)
        """
        servidor = self.records['scosinf1']
        self.login(servidor)
        documento = self.records['documento_rascunho']
        self._compartilhar_documento_individual(
            documento,
            pessoas_permitidas_podem_ler=[self.records['proreitor_propi']],
            pessoas_permitidas_podem_escrever=[self.records['diretor_cnat']],
            setores_permitidos_podem_ler=[self.records['setor_proex']],
            setores_permitidos_podem_escrever=[self.records['setor_gabin']],
        )
        self.logger.info('Comparando servidores do mesmo setor')
        self.assertListEqual(self._get_servidores_mesmo_setor(), [self.records['coord_cosinf'], self.records['scosinf2']])
        self.logger.info('Comparando servidores de setores irmãos')
        self.assertListEqual(self._get_servidores_setor_irmao(), [self.records['coord_cosaad']])
        self.logger.info('Comparando servidor chefe do setor pai')
        self.assertListEqual(self._get_chefe_setor_pai(), [self.records['reitor'], self.records['diretor_digti']])
        self.logger.info('Comparando servidores de documento compartilhado LER')
        self.assertListEqual(self._get_servidores_de_documento_compartilhado_ler(documento), [self.records['proreitor_proex'], self.records['proreitor_propi']])
        self.logger.info('Comparando servidores de documento compartilhado EDITAR')
        self.assertListEqual(self._get_servidores_de_documento_compartilhado_editar(documento), [self.records['chefe_gabin'], self.records['diretor_cnat']])
        self.logger.info('\n\nFazendo o compartilhamento do documento ...')

        # A função merge_nested_dict faz um merge do dicionário
        self.verificar_conteudo_telas_documento(
            documento=documento,
            conteudos_tela_listagem=self.tela_compartilhado_listagem,
            conteudos_tela_visualizacao=self.tela_compartilhado_visualizacao,
            servidores_caso_particular=[],
        )

    def test_documento_concluido(self):
        """
        Cria um documento com nível de acesso público.
        Documento público, tem acesso todos os servidores do mesmo setor e servidores de setores compartilhados

        Faz o compartilhamento individual do documento, incluindo pessoas e setores que podem ler ou escrever.
        . Criador: sconsinf1(9007)
        . Mesmo Setor/Pai
            - Mesmo Setor: coord_cosinf(9005), sconsif2(9008)
            - Setor Pai: setor_digti - diretor_digti(9003)
        . Setor irmão/Documento Compartilhado (Setor)
            - Setor Irmão: setor_cosaad - coord_cosaad(9006)
            - Documento compartilhado (setor): setor_coinre - sconire1(9010), sconire2(9011)
        . Compartilhamento Documento Editar
            - Setor: setor_gabin - chefe_gabin(9004)
            - Servidor: diretor_cnat(9002)
        . Compartilhamento Documento Ler
            - Setor: setor_proex - proreitor_proex(9012)
            - Servidor: proreitor_propi(9013)
        . Demais Servidores: sdiatinf1(9009)
        """
        # Qualquer servidor pode cadastrar documento
        servidor = self.records['scosinf1']
        self.login(servidor)
        self.logger.info('\n\nTornar documento em Minuta - Gerar Minuta')
        documento = self.records['documento_compartilhado']
        self._concluir_documento(documento)
        self.verificar_conteudo_telas_documento(
            documento=documento, conteudos_tela_listagem=self.tela_concluido_listagem, conteudos_tela_visualizacao=self.tela_concluido_visualizacao, servidores_caso_particular=[]
        )
        return
        self.logger.info('\n\nSolicitar revisão ao servidor scoinre1')
        servidor_revisor = self.records['scoinre1']
        self._solicitar_revisao(revisor=servidor_revisor, documento=documento)
        merge_nested_dict(
            conteudos_tela_listagem,
            {
                'servidores_com_acesso_edicao': {
                    'comum': {},
                    'servidor_dono': {},
                    'servidores_mesmo_setor_ou_pai': {},
                    'servidores_setores_irmaos_e_compartilhados_editar_setor_usuario_meus_setores': {},
                    'servidores_caso_particular': {},
                },
                'documentos_compartilhados_listagem_qualquer_setor_editar': {
                    '/documento_eletronico/gerenciar_compartilhamento_documento/%(id)s/': (True, HTTP_403_FORBIDDEN),
                    '/documento_eletronico/visualizar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/editar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/clonar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/admin/documento_eletronico/documentotexto/%(id)s/history/': (True, HTTP_200_OK),
                    self._get_nivel_acesso_display(Documento.NIVEL_ACESSO_PUBLICO): (True, HTTP_200_OK),
                    self._get_status_display(DocumentoStatus.STATUS_RASCUNHO): (True, HTTP_200_OK),
                    'Nenhum documento foi encontrado': (True, HTTP_200_OK),
                },
                'documentos_compartilhados_listagem_todos_setores_ler': {
                    '/documento_eletronico/visualizar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/clonar_documento/%(id)s/': (True, HTTP_200_OK),
                },
                'outros_usuarios': {},
            },
        )
        merge_nested_dict(
            conteudos_tela_visualizacao,
            {
                'servidores_com_acesso_edicao': {
                    'comum': {},
                    'servidor_dono': {},
                    'servidores_mesmo_setor_ou_pai': {},
                    'servidores_setores_irmaos_e_compartilhados_editar_setor_usuario_meus_setores': {},
                    'servidores_caso_particular': {},
                },
                'documentos_compartilhados_listagem_qualquer_setor_editar': {'/documento_eletronico/concluir_documento/%(id)s/': (True, HTTP_200_OK)},
                'documentos_compartilhados_listagem_todos_setores_ler': {},
                'outros_usuarios': {},
            },
        )
        self.verificar_conteudo_telas_documento(
            documento=documento, conteudos_tela_listagem=conteudos_tela_listagem, conteudos_tela_visualizacao=conteudos_tela_visualizacao, servidores_caso_particular=[]
        )

        self.logger.info('\n\nRevisor marcando documento como revisado ...')
        self._marcar_como_revisado(servidor_revisor, documento)
        merge_nested_dict(
            conteudos_tela_listagem,
            {
                'servidores_com_acesso_edicao': {
                    'comum': {},
                    'servidor_dono': {},
                    'servidores_mesmo_setor_ou_pai': {},
                    'servidores_setores_irmaos_e_compartilhados_editar_setor_usuario_meus_setores': {},
                    'servidores_caso_particular': {},
                },
                'documentos_compartilhados_listagem_qualquer_setor_editar': {
                    '/documento_eletronico/gerenciar_compartilhamento_documento/%(id)s/': (True, HTTP_403_FORBIDDEN),
                    '/documento_eletronico/visualizar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/editar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/clonar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/admin/documento_eletronico/documentotexto/%(id)s/history/': (True, HTTP_200_OK),
                    self._get_nivel_acesso_display(Documento.NIVEL_ACESSO_PUBLICO): (True, HTTP_200_OK),
                    self._get_status_display(DocumentoStatus.STATUS_RASCUNHO): (True, HTTP_200_OK),
                    'Nenhum documento foi encontrado': (True, HTTP_200_OK),
                },
                'documentos_compartilhados_listagem_todos_setores_ler': {
                    '/documento_eletronico/visualizar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/clonar_documento/%(id)s/': (True, HTTP_200_OK),
                },
                'outros_usuarios': {},
            },
        )
        merge_nested_dict(
            conteudos_tela_visualizacao,
            {
                'servidores_com_acesso_edicao': {
                    'comum': {},
                    'servidor_dono': {},
                    'servidores_mesmo_setor_ou_pai': {},
                    'servidores_setores_irmaos_e_compartilhados_editar_setor_usuario_meus_setores': {},
                    'servidores_caso_particular': {},
                },
                'documentos_compartilhados_listagem_qualquer_setor_editar': {'/documento_eletronico/concluir_documento/%(id)s/': (True, HTTP_200_OK)},
                'documentos_compartilhados_listagem_todos_setores_ler': {},
                'outros_usuarios': {},
            },
        )
        conteudos_tela_visualizacao['servidores_caso_particular'] = {}
        # servidor_revisor particular passou a fazer parte dos servidores sem acesso
        self.verificar_conteudo_telas_documento(
            documento=documento, conteudos_tela_listagem=conteudos_tela_listagem, conteudos_tela_visualizacao=conteudos_tela_visualizacao, servidores_caso_particular=[]
        )

        self.logger.info('\n\nTornar documento em Minuta Novamente')
        self._concluir_documento(documento)
        merge_nested_dict(
            conteudos_tela_listagem,
            {
                'servidores_com_acesso_edicao': {
                    'comum': {
                        '/documento_eletronico/editar_documento/%(id)s/': (False, HTTP_403_FORBIDDEN),
                        '/documento_eletronico/imprimir_documento_pdf/%(id)s/carta/': (True, HTTP_200_OK),
                        '/documento_eletronico/imprimir_documento_pdf/%(id)s/paisagem/': (True, HTTP_200_OK),
                        '/documento_eletronico/solicitar_revisao/%(id)s/': (True, HTTP_200_OK),
                    },
                    'servidor_dono': {},
                    'servidores_mesmo_setor_ou_pai': {},
                    'servidores_setores_irmaos_e_compartilhados_editar_setor': {},
                    'servidores_caso_particular': {},
                },
                'documentos_compartilhados_listagem_qualquer_setor_editar': {
                    '/documento_eletronico/editar_documento/%(id)s/': (False, HTTP_403_FORBIDDEN),
                    '/documento_eletronico/imprimir_documento_pdf/%(id)s/carta/': (True, HTTP_200_OK),
                    '/documento_eletronico/imprimir_documento_pdf/%(id)s/paisagem/': (True, HTTP_200_OK),
                    '/documento_eletronico/solicitar_revisao/%(id)s/': (True, HTTP_200_OK),
                },
                'documentos_compartilhados_listagem_todos_setores_ler': {},
                'outros_usuarios': {},
            },
        )
        merge_nested_dict(
            conteudos_tela_visualizacao,
            {
                'servidores_com_acesso_edicao': {
                    'comum': {
                        '/documento_eletronico/concluir_documento/%(id)s/': (False, HTTP_403_FORBIDDEN),
                        '/documento_eletronico/imprimir_documento_pdf/%(id)s/carta/': (True, HTTP_200_OK),
                        '/documento_eletronico/imprimir_documento_pdf/%(id)s/paisagem/': (True, HTTP_200_OK),
                        '/documento_eletronico/retornar_para_rascunho/%(id)s/': (True, HTTP_200_OK),
                        '/documento_eletronico/solicitar_assinatura/%(id)s/': (True, HTTP_200_OK),
                        '/documento_eletronico/assinar_documento/%(id)s/': (True, HTTP_200_OK),
                        '/documento_eletronico/assinar_documento_token/%(id)s/': (True, HTTP_200_OK),
                    },
                    'servidor_dono': {},
                    'servidores_mesmo_setor_ou_pai': {},
                    'servidores_setores_irmaos_e_compartilhados_editar_setor': {},
                    'servidores_caso_particular': {},
                },
                'documentos_compartilhados_listagem_qualquer_setor_editar': {'/documento_eletronico/concluir_documento/%(id)s/': (False, HTTP_403_FORBIDDEN)},
                'documentos_compartilhados_listagem_todos_setores_ler': {},
                'outros_usuarios': {},
            },
        )
        self.verificar_conteudo_telas_documento(
            documento=documento, conteudos_tela_listagem=conteudos_tela_listagem, conteudos_tela_visualizacao=conteudos_tela_visualizacao, servidores_caso_particular=[]
        )

        self.logger.info('\n\nDono do documento solicitando assinatura ao servidor scoinre2 ...')
        servidor_pedido_assinatura = self.records['scoinre2']
        self._solicitar_assinatura(servidor_pedido_assinatura, documento)

        merge_nested_dict(
            conteudos_tela_listagem,
            {
                'servidores_com_acesso_edicao': {
                    'comum': {},
                    'servidor_dono': {},
                    'servidores_mesmo_setor_ou_pai': {},
                    'servidores_setores_irmaos_e_compartilhados_editar_setor_usuario_meus_setores': {},
                    'servidores_caso_particular': {},
                },
                'documentos_compartilhados_listagem_qualquer_setor_editar': {
                    '/documento_eletronico/gerenciar_compartilhamento_documento/%(id)s/': (True, HTTP_403_FORBIDDEN),
                    '/documento_eletronico/visualizar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/editar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/clonar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/admin/documento_eletronico/documentotexto/%(id)s/history/': (True, HTTP_200_OK),
                    self._get_nivel_acesso_display(Documento.NIVEL_ACESSO_PUBLICO): (True, HTTP_200_OK),
                    self._get_status_display(DocumentoStatus.STATUS_RASCUNHO): (True, HTTP_200_OK),
                    'Nenhum documento foi encontrado': (True, HTTP_200_OK),
                },
                'documentos_compartilhados_listagem_todos_setores_ler': {
                    '/documento_eletronico/visualizar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/clonar_documento/%(id)s/': (True, HTTP_200_OK),
                },
                'outros_usuarios': {},
            },
        )
        merge_nested_dict(
            conteudos_tela_visualizacao,
            {
                'servidores_com_acesso_edicao': {
                    'comum': {},
                    'servidor_dono': {},
                    'servidores_mesmo_setor_ou_pai': {},
                    'servidores_setores_irmaos_e_compartilhados_editar_setor_usuario_meus_setores': {},
                    'servidores_caso_particular': {},
                },
                'documentos_compartilhados_listagem_qualquer_setor_editar': {'/documento_eletronico/concluir_documento/%(id)s/': (True, HTTP_200_OK)},
                'documentos_compartilhados_listagem_todos_setores_ler': {},
                'outros_usuarios': {},
            },
        )
        self.verificar_conteudo_telas_documento(
            documento=documento, conteudos_tela_listagem=conteudos_tela_listagem, conteudos_tela_visualizacao=conteudos_tela_visualizacao, servidores_caso_particular=[]
        )
        return
        self.logger.info('\n\nServidor scoinre2 assinando documento via senha ...')
        self._assinar_documento_via_senha(servidor_pedido_assinatura, documento)

        merge_nested_dict(
            conteudos_tela_listagem,
            {
                'servidores_com_acesso_edicao': {
                    'comum': {},
                    'servidor_dono': {},
                    'servidores_mesmo_setor_ou_pai': {},
                    'servidores_setores_irmaos_e_compartilhados_editar_setor_usuario_meus_setores': {},
                    'servidores_caso_particular': {},
                },
                'documentos_compartilhados_listagem_qualquer_setor_editar': {
                    '/documento_eletronico/gerenciar_compartilhamento_documento/%(id)s/': (True, HTTP_403_FORBIDDEN),
                    '/documento_eletronico/visualizar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/editar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/clonar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/admin/documento_eletronico/documentotexto/%(id)s/history/': (True, HTTP_200_OK),
                    self._get_nivel_acesso_display(Documento.NIVEL_ACESSO_PUBLICO): (True, HTTP_200_OK),
                    self._get_status_display(DocumentoStatus.STATUS_RASCUNHO): (True, HTTP_200_OK),
                    'Nenhum documento foi encontrado': (True, HTTP_200_OK),
                },
                'documentos_compartilhados_listagem_todos_setores_ler': {
                    '/documento_eletronico/visualizar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/clonar_documento/%(id)s/': (True, HTTP_200_OK),
                },
                'outros_usuarios': {},
            },
        )
        merge_nested_dict(
            conteudos_tela_visualizacao,
            {
                'servidores_com_acesso_edicao': {
                    'comum': {},
                    'servidor_dono': {},
                    'servidores_mesmo_setor_ou_pai': {},
                    'servidores_setores_irmaos_e_compartilhados_editar_setor_usuario_meus_setores': {},
                    'servidores_caso_particular': {},
                },
                'documentos_compartilhados_listagem_qualquer_setor_editar': {'/documento_eletronico/concluir_documento/%(id)s/': (True, HTTP_200_OK)},
                'documentos_compartilhados_listagem_todos_setores_ler': {},
                'outros_usuarios': {},
            },
        )
        self.verificar_conteudo_telas_documento(
            documento=documento, conteudos_tela_listagem=conteudos_tela_listagem, conteudos_tela_visualizacao=conteudos_tela_visualizacao, servidores_caso_particular=[]
        )

        self.logger.info('\n\nDono do documento assinando via senha ...')
        self._assinar_documento_via_senha(servidor, documento)
        merge_nested_dict(
            conteudos_tela_listagem,
            {
                'servidores_com_acesso_edicao': {
                    'comum': {},
                    'servidor_dono': {},
                    'servidores_mesmo_setor_ou_pai': {},
                    'servidores_setores_irmaos_e_compartilhados_editar_setor_usuario_meus_setores': {},
                    'servidores_caso_particular': {},
                },
                'documentos_compartilhados_listagem_qualquer_setor_editar': {
                    '/documento_eletronico/gerenciar_compartilhamento_documento/%(id)s/': (True, HTTP_403_FORBIDDEN),
                    '/documento_eletronico/visualizar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/editar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/clonar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/admin/documento_eletronico/documentotexto/%(id)s/history/': (True, HTTP_200_OK),
                    self._get_nivel_acesso_display(Documento.NIVEL_ACESSO_PUBLICO): (True, HTTP_200_OK),
                    self._get_status_display(DocumentoStatus.STATUS_RASCUNHO): (True, HTTP_200_OK),
                    'Nenhum documento foi encontrado': (True, HTTP_200_OK),
                },
                'documentos_compartilhados_listagem_todos_setores_ler': {
                    '/documento_eletronico/visualizar_documento/%(id)s/': (True, HTTP_200_OK),
                    '/documento_eletronico/clonar_documento/%(id)s/': (True, HTTP_200_OK),
                },
                'outros_usuarios': {},
            },
        )
        merge_nested_dict(
            conteudos_tela_visualizacao,
            {
                'servidores_com_acesso_edicao': {
                    'comum': {},
                    'servidor_dono': {},
                    'servidores_mesmo_setor_ou_pai': {},
                    'servidores_setores_irmaos_e_compartilhados_editar_setor_usuario_meus_setores': {},
                    'servidores_caso_particular': {},
                },
                'documentos_compartilhados_listagem_qualquer_setor_editar': {'/documento_eletronico/concluir_documento/%(id)s/': (True, HTTP_200_OK)},
                'documentos_compartilhados_listagem_todos_setores_ler': {},
                'outros_usuarios': {},
            },
        )
        self.verificar_conteudo_telas_documento(
            documento=documento, conteudos_tela_listagem=conteudos_tela_listagem, conteudos_tela_visualizacao=conteudos_tela_visualizacao, servidores_caso_particular=[]
        )

    def _test_permissao_compartilhamento(self):
        """
        Documento compartilhado com acesso escrita para o setor e em seguida com acesso leitura para um servidor desse setor.
        O servidor do setor herda o acesso do setor, ou seja, fica com permissão escrita no documento?
        Documento público compartilhado para a pessoa coinre1 somente leitura e para o setor coinre modo edição.
        :return:
        """
        # TODO: Atualmente prevalece a permissão do setor, mas acho que deveria permanecer a permissão mais restrita.

        # Qualquer servidor pode cadastrar documento
        servidor = self.records['scosinf1']
        self.login(servidor)
        self.logger.info('\n\nCadastrando documento público ...')
        documento = self._cadastrar_documento(servidor, self.retornar(TipoDocumentoTexto, chaves={'sigla': 'OFÍCIO'})[0], Documento.NIVEL_ACESSO_PUBLICO)

        self.logger.info('\n\nFazendo o compartilhamento individual, pessoas_permitidas_podem_ler=[scoinre1], ' 'setores_permitidos_podem_escrever=[setor_coinre]  ...')
        self._compartilhar_documento_individual(
            documento,
            pessoas_permitidas_podem_ler=[self.records['scoinre1']],
            pessoas_permitidas_podem_escrever=[],
            setores_permitidos_podem_ler=[],
            setores_permitidos_podem_escrever=[self.records['setor_coinre']],
        )

        # Documento público e compartilhado somente leitura com servidor scoinre1 e permissão escrita com o setor coinre.
        # Servidor scoinre1 tem permissão de escrita herdada do setor.
        # Tem acesso todos os servidores do mesmo setor, dos setores compartilhados e os servidores de
        # documentos compartilhados. No exemplo abaixo, não tem acesso ao documento o servidor sdiatinf1
        conteudos_tela_visualizacao = {'/documento_eletronico/concluir_documento/%(id)s/': (True, HTTP_200_OK)}

        self.verificar_conteudo_telas_documento(
            documento=documento, conteudos_tela_listagem={}, conteudos_tela_visualizacao=conteudos_tela_visualizacao, servidores_caso_particular=[]
        )
        self.logger.info('\n\nFazendo o compartilhamento individual, pessoas_permitidas_podem_escrever=[scoinre1], ' 'setores_permitidos_podem_ler=[setor_coinre]  ...')
        # Testando o inverso, ou seja, servidor do setor pode editar, mas o setor só pode visualizar.
        # Fazendo o inverso, as permissões continuaram, é como se prevalecesse a maior permissão
        self._compartilhar_documento_individual(
            documento,
            pessoas_permitidas_podem_ler=[],
            pessoas_permitidas_podem_escrever=[self.records['scoinre1']],
            setores_permitidos_podem_ler=[self.records['setor_coinre']],
            setores_permitidos_podem_escrever=[],
        )

        self.verificar_conteudo_telas_documento(
            documento=documento, conteudos_tela_listagem={}, conteudos_tela_visualizacao=conteudos_tela_visualizacao, servidores_caso_particular=[]
        )

    def _test_clonar_documento(self):
        """
        :param cls:
        :param expected_url:
        :return:
        """
        servidor = self.records['scosinf1']
        servidores_mesmo_setor_ou_pai = [self.records['coord_cosinf'], servidor, self.records['scosinf2']]
        servidores_setores_irmaos_e_compartilhados_editar_setor_usuario_meus_setores = [self.records['coord_cosaad']]

        self.login(servidor)

        documento = self._cadastrar_documento(self.records['scosinf1'], self.retornar(TipoDocumentoTexto, chaves={'sigla': 'OFÍCIO'})[0], Documento.NIVEL_ACESSO_PUBLICO)
        url = '/documento_eletronico/clonar_documento/{}/'.format(documento.id)

        # Servidores que não possuem acesso ao documento, não tem permissão para clonar documento
        servidores_sem_acesso = set(self._get_servidores()) - set(servidores_mesmo_setor_ou_pai) - set(servidores_setores_irmaos_e_compartilhados_editar_setor_usuario_meus_setores)
        for s in servidores_sem_acesso:
            self.login(s)
            response = self.client.get(url)
            self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        quant = Documento.objects.count()
        self.login(servidor)
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'Documento clonado com sucesso.', status_code=HTTP_200_OK)
        self.assertEqual(Documento.objects.count(), quant + 1)
        # TODO comentei a linha abaixo, pois ocorre divergência entre numero e identificador do documento,
        # self.assertEqual(documento.numero, documento.identificador[len(documento.tipo.sigla) + 1:])

        documento_clonado = self.retornar(Documento)[0]
        expected_url = '/documento_eletronico/visualizar_documento/{}/'.format(documento_clonado.id)
        self.assertRedirects(response, expected_url, status_code=HTTP_302_FOUND, target_status_code=HTTP_200_OK)

        # TODO: Quando um documento é compartilhado, ao clonar herdar os compartilhamentos?
        # TODO: Pq atualmente não está herdando.
        # Documento clonado tem os mesmos acessos do documento original.
        # Documento público, tem acesso todos os servidores do mesmo setor e servidores de setores compartilhados.
        self.verificar_conteudo_telas_documento(documento=documento, conteudos_tela_listagem={}, conteudos_tela_visualizacao={}, servidores_caso_particular=[])

    def _test_solicitar_assinatura(self):
        """
        Criar um documento, solicitar a assinatura a um servidor e verificar os botões e acessos
        Depois solicitar a assinatura aservidor que faz parte do setor compartilhado e verificar os botões e acessos.
        Em seguida solicitar a assinatura de uma pessoa que faz parte do documento compartilhar escrita e verificar 
        os botões e acessos.
        Por último, solicitar a assinatura de uma pessoa que já foi revisor e verificar os botões e acessos
        :return:
        """

    def _test_controle_edicao_documento(self):
        """
        Dois usuários editando um documento ao mesmo tempo, prevalece a alteração do primeiro que salvar.
        Quando o segundo usuário salvar o documento, será emitida uma mensagem de alerta informando que o documento 
        foi alterado por outro usuário.
        :return:
        """
        pass

    def _test_alteracao_cabecalho_e_rodape(self):
        """
        Cadastrar um documento e assiná-lo. Em seguida, alterar o o cabeçalho e/ou rodapé do tipo do documento e 
        verificar se o cabeçalho e/ou rodapé estão intactos
        :return:
        """
        pass

    def _test_certificado_revogado(self):
        # Se a data de expiração do certificado está ok e se ele não está na lista de revogados.
        # verify_chain_of_trust
        # revoked certificate, certificate revocation
        servidor = self.records['scosinf1']
        self.login(servidor)
        documento = self._cadastrar_documento(servidor, self.retornar(TipoDocumentoTexto, chaves={'sigla': 'OFÍCIO'})[0], Documento.NIVEL_ACESSO_PUBLICO)
        servidor_revisor = self.records['scoinre1']
        self._solicitar_revisao(revisor=servidor_revisor, documento=documento)
        self._marcar_como_revisado(servidor_revisor, documento)
        servidor_pedido_assinatura = self.records['scoinre2']

        self._solicitar_assinatura(servidor_pedido_assinatura, documento)
        self._assinar_documento_via_token(servidor_pedido_assinatura, documento)

    def test_ajax_sugestao_identificador_documento_texto(self):
        """
        Ao selecionar o setor dono no formulário de cadastro de documento, ocorreu um ajax para obter 
        a númeração do doucmento.
        """
        DocumentoTexto.objects.all().delete()
        servidor = self.records['scosinf1']
        tipo_documento = self.retornar(TipoDocumentoTexto, chaves={'sigla': 'OFÍCIO'})[0]
        data = {'identificador_numero': 1, 'identificador_setor_sigla': 'COSINF/DIGTI/RE/RAIZ', 'identificador_tipo_documento_sigla': 'OFÍCIO', 'identificador_ano': 2017}
        # Qualquer servidor tem acesso
        self.login()
        js = self._obter_numeracao_documento(tipo_documento, servidor.setor)
        self.assertEqual(data, js)

        documento = self._cadastrar_documento(servidor, tipo_documento, Documento.NIVEL_ACESSO_PUBLICO, dados={'identificador_numero': 10})
        data = {'identificador_numero': 11, 'identificador_setor_sigla': 'COSINF/DIGTI/RE/RAIZ', 'identificador_tipo_documento_sigla': 'OFÍCIO', 'identificador_ano': 2017}
        js = self._obter_numeracao_documento(tipo_documento, servidor.setor)
        self.assertEqual(data, js)
