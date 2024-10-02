from rest_framework import serializers
from .models import Servico, RegistroAcompanhamentoGovBR, RegistroAvaliacaoGovBR, Solicitacao
from catalogo_provedor_servico.providers.factory import get_service_provider_factory
from catalogo_provedor_servico.services import atualizar_registro_avaliacao


class ServicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servico
        fields = ['icone', 'id_servico_portal_govbr', 'titulo', 'descricao']


class AvaliacaoDisponibilidadeServicoSerializer(serializers.Serializer):
    servico = ServicoSerializer()
    cpf = serializers.CharField()
    criterios_sucesso = serializers.CharField()
    criterios_erro = serializers.CharField()
    is_ok = serializers.BooleanField()


class RegistroAcompanhamentoGovBRSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroAcompanhamentoGovBR
        fields = '__all__'

    def to_representation(self, obj):
        return {
            'servico': self.get_servico(obj),
            'protocolo': self.get_protocolo(obj),
            'etapa': self.get_etapa(obj),
            'dataEtapa': self.get_dataEtapa(obj),
            'situacaoEtapa': self.get_situacaoEtapa(obj),
            'dataSituacaoEtapa': self.get_dataSituacaoEtapa(obj),
            'orgao': self.get_orgao(obj),
            'nome_servico': self.get_nome_servico(obj),
            'url_avaliacao': self.get_url_avaliacao(obj),
        }

    def get_servico(self, obj):
        return obj.payload['servico']

    def get_protocolo(self, obj):
        return obj.payload['protocolo']

    def get_etapa(self, obj):
        return get_situacao_display(obj.payload['etapa'])

    def get_dataEtapa(self, obj):
        return obj.payload['dataEtapa']

    def get_situacaoEtapa(self, obj):
        return obj.payload['situacaoEtapa']

    def get_dataSituacaoEtapa(self, obj):
        return obj.data_criacao.strftime('%d/%m/%Y - %H:%M:%S')

    def get_orgao(self, obj):
        return obj.payload['orgao']

    def get_nome_servico(self, obj):
        return obj.solicitacao.servico.titulo

    def get_url_avaliacao(self, obj):
        if 'etapa' in obj.payload and obj.payload['etapa'] == 'ATENDIDO':
            if RegistroAvaliacaoGovBR.objects.filter(solicitacao=obj.solicitacao).exists():
                registroavaliacao = RegistroAvaliacaoGovBR.objects.filter(solicitacao=obj.solicitacao)[0]
                if not registroavaliacao.url_avaliacao:
                    service_provider = get_service_provider_factory().get_service_provider(id_servico_portal_govbr=obj.solicitacao.servico.id_servico_portal_govbr)
                    service_provider.obter_formulario_avaliacao(obj.solicitacao)
                elif not registroavaliacao.avaliado and obj.solicitacao.status == Solicitacao.STATUS_ATENDIDO:
                    atualizar_registro_avaliacao(obj)
                elif registroavaliacao.avaliado:
                    return "Avaliado"
                return registroavaliacao.url_avaliacao
        else:
            return None


def get_situacao_display(etapa):
    for situacao in Solicitacao.STATUS_CHOICES:
        if situacao[0] == etapa:
            return situacao[1]
    return etapa
