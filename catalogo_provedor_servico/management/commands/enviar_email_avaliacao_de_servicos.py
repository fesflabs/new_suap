import tqdm
from djtools.management.commands import BaseCommandPlus

from catalogo_provedor_servico.models import RegistroAvaliacaoGovBR, RegistroAcompanhamentoGovBR
from catalogo_provedor_servico.providers.factory import get_service_provider_factory
from catalogo_provedor_servico.services import registrar_acompanhamento_servico
from catalogo_provedor_servico.utils import Notificar


# Exemplo de chamada:
# python manage.py enviar_email_avaliacao_de_servicos


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        verbose = str(options.get('verbosity', '0')) != '0'

        # Envia registros de acompanhamentos pendentes, pois o link da url de avaliação só pode é retornado se existir
        # o acompanhamento registrado anteriormente
        registros_acompanhamentos_nao_enviados = RegistroAcompanhamentoGovBR.objects.filter(status__in=[RegistroAcompanhamentoGovBR.PENDENTE, RegistroAcompanhamentoGovBR.ERRO], tentativas_envio__lte=3)

        print('Tentando obter as avaliação de solicitações com o govbr.')
        if verbose:
            registros_acompanhamentos_nao_enviados = tqdm.tqdm(registros_acompanhamentos_nao_enviados)

        for registro_acompanhamento in registros_acompanhamentos_nao_enviados:
            if registro_acompanhamento.tipo == RegistroAcompanhamentoGovBR.TIPO_ACOMPANHAMENTO:
                registrar_acompanhamento_servico(registro=registro_acompanhamento)

        # Verifica se existem registros não notificados para obter link da url
        registros_avaliacao_pendente_url = RegistroAvaliacaoGovBR.objects.filter(notificado_por_email=False, avaliado=False, tentativas_envio__lte=4)

        if not registros_avaliacao_pendente_url.exists():
            print('Nenhuma solicitação com e-mail de avaliação pendente.')
            return
        else:
            print('Tentando enviar as avaliação de solicitações para os solicitantes.')

        if verbose:
            registros_avaliacao_pendente_url = tqdm.tqdm(registros_avaliacao_pendente_url)

        for registro in registros_avaliacao_pendente_url:
            service_provider = get_service_provider_factory().get_service_provider(id_servico_portal_govbr=registro.solicitacao.servico.id_servico_portal_govbr)
            url_avaliacao = registro.url_avaliacao
            if not url_avaliacao:
                service_provider.obter_formulario_avaliacao(registro.solicitacao, verbose=True)
            dados_email = service_provider.get_dados_email(solicitacao=registro.solicitacao)
            if url_avaliacao:
                Notificar.notifica_conclusao_servico_atendido(solicitacao=registro.solicitacao, dados_email=dados_email, url_avaliacao=url_avaliacao)
                if registro.notificado_por_email:
                    print("E-MAIL ENVIADO para solicitação {}".format(registro.solicitacao.id))
                else:
                    registro.tentativas_envio = registro.tentativas_envio + 1
                    registro.save()
                    print("Url de avaliação salva porém houve ERRO AO ENVIAR E-MAIL para solicitação {}".format(registro.solicitacao.id))
