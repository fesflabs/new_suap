"""
Comando que importa os dados de vacinação do usuário diretamente do RNMAISVACINA
"""
import datetime
import json
import requests

from comum.models import Vinculo, Configuracao
from djtools.management.commands import BaseCommandPlus
from rh.models import UnidadeOrganizacional
from saude.models import PassaporteVacinalCovid, Vacina, CartaoVacinal, Prontuario


class EmptyResponse(Exception):
    pass


class Command(BaseCommandPlus):
    help = 'Executa os testes do SUAP'

    def add_arguments(self, parser):
        parser.add_argument('--cpf', '-cpf', dest='cpf', action='store', default=[], help='CPF.')
        parser.add_argument('--vinculo', '-v', dest='vinculo', action='store', default=[], help='Vinculo.')
        parser.add_argument('--campus', '-c', dest='campus', action='store', default=[], help='Campus.')

    def handle(self, *args, **options):
        # usar ./manage.py importar_dados_rnmaisvacina --cpf=32168954089 --vinculo=1633365
        cpf = options.get('cpf', None)
        vinculo_id = options.get('vinculo', None)
        campus = options.get('campus', None)
        count_exceptions = 0
        host = Configuracao.get_valor_por_chave('saude', 'host_rnmaisvacina')
        token = Configuracao.get_valor_por_chave('saude', 'token_rnmaisvacina')
        if host and token and cpf:
            cpf_sem_mascara = cpf.replace('.', '').replace('-', '')
            url = '{}/api/cidadao_vacinas/'.format(host)
            headers = {'Authorization': 'Token {}'.format(token)}
            json_cpf = {"cpf_cns": cpf_sem_mascara}
            response = requests.post(url, headers=headers, json=json_cpf)
            try:
                retorno = json.loads(response.text)
            except Exception:
                return 'erro'
            if 'errors' in retorno:
                if len(cpf_sem_mascara) == 11:
                    vinculo = Vinculo.objects.get(id=vinculo_id)
                    if not PassaporteVacinalCovid.objects.filter(vinculo_id=vinculo_id).exists():
                        passaporte = PassaporteVacinalCovid()
                        passaporte.vinculo = vinculo
                        passaporte.uo = UnidadeOrganizacional.objects.get(id=campus)
                        passaporte.cpf = cpf_sem_mascara
                    else:
                        passaporte = PassaporteVacinalCovid.objects.get(vinculo_id=vinculo_id)
                        passaporte.atualizado_em = datetime.datetime.now()

                    passaporte.recebeu_alguma_dose = False
                    if passaporte.possui_atestado_medico is None and passaporte.termo_aceito_em is None and not passaporte.cartao_vacinal_cadastrado_em:
                        passaporte.situacao_declaracao = PassaporteVacinalCovid.AGUARDANDO_AUTODECLARACAO
                    passaporte.save()
                count_exceptions = 1
                return count_exceptions
            elif 'detail' in retorno:
                count_exceptions = 1
                return count_exceptions
            else:
                retorno = retorno[0]
                if 'rotina' in retorno and len(cpf_sem_mascara) == 11:
                    vinculo = Vinculo.objects.get(id=vinculo_id)
                    if not PassaporteVacinalCovid.objects.filter(vinculo_id=vinculo_id).exists():
                        passaporte = PassaporteVacinalCovid()
                        passaporte.vinculo = vinculo
                        passaporte.uo = UnidadeOrganizacional.objects.get(id=campus)
                        passaporte.cpf = cpf_sem_mascara
                    else:
                        passaporte = PassaporteVacinalCovid.objects.get(vinculo_id=vinculo_id)
                        passaporte.atualizado_em = datetime.datetime.now()
                    passaporte.tem_cadastro = True
                    if retorno['ultima_dose'] == 0:
                        passaporte.recebeu_alguma_dose = False
                        if passaporte.possui_atestado_medico is None and passaporte.termo_aceito_em is None and not passaporte.cartao_vacinal_cadastrado_em:
                            passaporte.situacao_declaracao = PassaporteVacinalCovid.AGUARDANDO_AUTODECLARACAO
                    else:
                        passaporte.recebeu_alguma_dose = True
                        vacina_covid = False
                        if Vacina.objects.filter(eh_covid=True).exists():
                            vacina_covid = Vacina.objects.get(eh_covid=True)
                            prontuario = Prontuario.get_prontuario(vinculo)
                        if retorno['criticado'] == 1:
                            passaporte.tem_pendencia = True
                        else:
                            passaporte.tem_pendencia = False
                        if retorno['criticado'] == 0 or (retorno['ultima_dose'] + 1 >= retorno['total_doses']):
                            passaporte.situacao_passaporte = PassaporteVacinalCovid.VALIDO
                            passaporte.situacao_declaracao = PassaporteVacinalCovid.DEFERIDA
                            passaporte.esquema_completo = True
                        else:
                            if retorno['ultima_dose'] == 1:
                                passaporte.situacao_declaracao = PassaporteVacinalCovid.DEFERIDA
                        if 'doses_aplicadas' in retorno:
                            for reg in retorno['doses_aplicadas']:
                                data_vacinacao = datetime.datetime.strptime(reg['data_aplicacao'], '%Y-%m-%d')
                                data_aprazamento = (reg['data_aprazamento'] and datetime.datetime.strptime(reg['data_aprazamento'], '%Y-%m-%d')) or None
                                if reg['dose_esquema'] in ('1ª Dose', 'Única'):
                                    passaporte.data_primeira_dose = data_vacinacao
                                    if vacina_covid and not CartaoVacinal.objects.filter(prontuario=prontuario, vacina=vacina_covid, numero_dose=1).exists():
                                        CartaoVacinal.objects.get_or_create(prontuario=prontuario, data_prevista=data_aprazamento, vacina=vacina_covid, numero_dose=1, obs='Importado do RN+Vacina', data_vacinacao=data_vacinacao)
                                    if retorno['ultima_dose'] == 1 and reg['dose_esquema'] == '1ª Dose' and not (retorno['criticado'] == 0 or (retorno['ultima_dose'] + 1 >= retorno['total_doses'])):
                                        if data_aprazamento >= datetime.datetime.now():
                                            passaporte.situacao_passaporte = PassaporteVacinalCovid.PENDENTE
                                        else:
                                            passaporte.situacao_passaporte = PassaporteVacinalCovid.INVALIDO

                                elif reg['dose_esquema'] == '2ª Dose':
                                    passaporte.data_segunda_dose = data_vacinacao
                                    if vacina_covid and not CartaoVacinal.objects.filter(prontuario=prontuario, vacina=vacina_covid, numero_dose=2).exists():
                                        CartaoVacinal.objects.get_or_create(prontuario=prontuario, data_prevista=data_aprazamento, vacina=vacina_covid, numero_dose=2, obs='Importado do RN+Vacina', data_vacinacao=data_vacinacao)
                                else:
                                    passaporte.data_terceira_dose = data_vacinacao
                                    if vacina_covid and not CartaoVacinal.objects.filter(prontuario=prontuario, vacina=vacina_covid, numero_dose=3).exists():
                                        CartaoVacinal.objects.get_or_create(prontuario=prontuario, data_prevista=data_aprazamento, vacina=vacina_covid, numero_dose=3, obs='Importado do RN+Vacina', data_vacinacao=data_vacinacao)

                    passaporte.save()
                    return count_exceptions
        else:
            return 'erro'
