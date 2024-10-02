# Funções sem iteração com a aplicação (página) ------------------------------------------------------------------------
from processo_eletronico.models import TipoProcesso

from behave import given
from django.apps import apps


@given('os cadastros básicos do módulo contratos')
def step_cadastros_do_modulo_demandas(context):
    from rh.models import PessoaJuridica, Servidor
    Processo = apps.get_model('processo_eletronico', 'processo')
    PessoaJuridica.objects.get_or_create(cnpj='45.006.424/0001-00', defaults=dict(nome='Pessoa Jurídica'))[0]
    servidor_fiscal = Servidor.objects.get(matricula='996622')
    gerente_contratos = Servidor.objects.get(matricula='996623')
    # Cadastra um processo do Protocolo
    tipo = TipoProcesso.objects.first()
    processo = Processo.objects.create(assunto="Assunto do Contrato", tipo_processo=tipo, setor_criacao=servidor_fiscal.setor, nivel_acesso=1, usuario_gerador=servidor_fiscal.user, modificado_por=servidor_fiscal.user)
    processo.interessados.add(servidor_fiscal.pessoa_fisica)
    processo.interessados.add(gerente_contratos.pessoa_fisica)
    processo.save()
