from catalogo_provedor_servico.models import Servico, Solicitacao
from catalogo_provedor_servico.providers.base import AvaliacaoDisponibilidadeServico
from catalogo_provedor_servico.providers.impl.ifrn.base import AbstractIfrnServiceProvider


class DefaultServiceProvider(AbstractIfrnServiceProvider):

    def __init__(self, id_servico_portal_govbr):
        self.id_servico_portal_govbr = id_servico_portal_govbr

    def get_id_servico_portal_govbr(self):
        return self.id_servico_portal_govbr

    def get_numero_total_etapas(self):
        return 1

    def get_avaliacao_disponibilidade(self, cpf, verbose=True):
        servico = Servico.objects.get(id_servico_portal_govbr=self.get_id_servico_portal_govbr())
        avaliacao = AvaliacaoDisponibilidadeServico(servico, cpf)
        avaliacao.add_criterio(servico.ativo, 'Serviço ativo.', 'Serviço inativo.')

        solicitacoes_em_aberto = Solicitacao.objects.filter(cpf=cpf, servico=servico).exclude(status__in=Solicitacao.STATUS_QUE_PERMITEM_HABILITACAO_SERVICO)
        avaliacao.add_criterio(not solicitacoes_em_aberto.exists(), 'Não há solicitações em aberto.', 'Existem solicitações em aberto.')

        # Negando o serviço, enquanto ele de fato não é implementado.
        avaliacao.add_criterio(False, 'Serviço disponível.', 'Serviço indisponível no momento.')
        return avaliacao

    def receber_solicitacao(self, request, cpf):
        raise NotImplementedError

    def get_dados_email(self, solicitacao):
        raise NotImplementedError

    def is_em_periodo_avaliacao(self, solicitacao, campus=None):
        raise NotImplementedError

    def executar_solicitacao(self, request, solicitacao):
        raise NotImplementedError
